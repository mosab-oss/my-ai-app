import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from huggingface_hub import InferenceClient
import io, base64, time, requests, urllib.parse
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# --- 1. الإعدادات ---
st.set_page_config(page_title="منصة مصعب v21", layout="wide", page_icon="🎤")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    section[data-testid="stSidebar"] {
        direction: rtl; text-align: right; background-color: #111;
    }
    .stSelectbox label, .stSlider label { color: #00ffcc !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. مفاتيح API ---
api_key        = st.secrets.get("GEMINI_API_KEY")
openai_key     = st.secrets.get("OPENAI_API_KEY")
hf_key         = st.secrets.get("HF_API_KEY")
together_key   = st.secrets.get("TOGETHER_API_KEY")
ideogram_key   = st.secrets.get("IDEOGRAM_API_KEY")
groq_key       = st.secrets.get("GROQ_API_KEY")
openrouter_key = st.secrets.get("OPENROUTER_API_KEY")
anthropic_key  = st.secrets.get("ANTHROPIC_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
if not any([api_key, groq_key, anthropic_key, openrouter_key]):
    st.error("⚠️ يجب وجود مفتاح API واحد على الأقل!")
    st.stop()

# --- 3. قوائم النماذج ---
ALL_CHAT_MODELS = {
    "Gemini 2.5 Flash":                       ("gemini-flash",    api_key),
    "Gemini 2.5 Pro":                         ("gemini-pro",      api_key),
    "Claude Sonnet 4 ★":                      ("claude-sonnet",   anthropic_key),
    "Claude Haiku 4 (سريع)":                  ("claude-haiku",    anthropic_key),
    "Claude عبر OpenRouter (مجاني)":          ("or-claude",       openrouter_key),
    "Groq LLaMA 3.3 70B":                     ("groq-llama",      groq_key),
    "Groq LLaMA 3.1 8B (سريع)":              ("groq-llama8b",    groq_key),
    "Groq Qwen3 32B":                         ("groq-qwen3",      groq_key),
    "Groq Llama 4 Scout":                     ("groq-llama4",     groq_key),
    "OpenRouter Auto (أفضل مجاني)":           ("or-auto",         openrouter_key),
    "OpenRouter DeepSeek R1 (مجاني)":         ("or-deepseek",     openrouter_key),
    "OpenRouter Llama 3.3 70B (مجاني)":       ("or-llama",        openrouter_key),
    "OpenRouter DeepSeek V3 (مجاني)":         ("or-dsv3",         openrouter_key),
    "DeepSeek R1 (محلي)":                     ("deepseek-local",  None),
}

# كل النماذج تظهر دائماً — التحقق من المفتاح يتم عند الاستخدام فقط
MODEL_MAP = {
    name: key
    for name, (key, secret) in ALL_CHAT_MODELS.items()
}

# علامة لمعرفة أي النماذج تحتاج مفتاح غير متاح (لعرض تحذير)
MODEL_NEEDS_KEY = {
    name: (secret is None and key != "deepseek-local")
    for name, (key, secret) in ALL_CHAT_MODELS.items()
}

ALL_IMAGE_MODELS = {
    "Pollinations FLUX (مجاني بلا مفتاح)":   ("poll-flux",   True),
    "Pollinations DALL-E (مجاني بلا مفتاح)": ("poll-dalle",  True),
    "Pollinations Turbo (مجاني بلا مفتاح)":  ("poll-turbo",  True),
    "Flux-Schnell (Hugging Face)":            ("flux-dev",    hf_key),
    "Stable Diffusion XL":                   ("sdxl",        hf_key),
    "DALL·E 3 (OpenAI)":                     ("dalle3",      openai_key),
    "Flux-Pro (Together AI)":                ("flux-pro",    together_key),
    "Ideogram v2":                           ("ideogram",    ideogram_key),
}

IMAGE_MODELS = {
    name: model_key
    for name, (model_key, secret) in ALL_IMAGE_MODELS.items()
    if secret
}

STYLE_MAP = {
    "واقعي":       "photorealistic, ultra detailed, high quality",
    "كرتوني":      "cartoon style, colorful, flat design",
    "زيتي":        "oil painting style, textured, classical",
    "خيال علمي":   "sci-fi, futuristic, neon lights",
    "أنيمي":       "anime style, manga illustration",
    "رسم بالقلم":  "pencil sketch, detailed line art",
    "مائي":        "watercolor painting, soft colors",
}

# --- 4. دوال توليد الصور ---

def generate_dalle(prompt):
    if not openai_key:
        raise Exception("مفتاح OPENAI_API_KEY غير موجود في الإعدادات")
    client = OpenAI(api_key=openai_key)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return "url", response.data[0].url


def generate_sdxl(prompt):
    if not hf_key:
        raise Exception("مفتاح HF_API_KEY غير موجود في الإعدادات")
    client = InferenceClient(api_key=hf_key)
    image = client.text_to_image(
        prompt=prompt,
        model="stabilityai/stable-diffusion-xl-base-1.0"
    )
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return "bytes", buf.getvalue()


# نماذج HF مرتبة حسب الأولوية
HF_MODELS_PRIORITY = [
    "black-forest-labs/FLUX.1-schnell",
    "black-forest-labs/FLUX.1-dev",
    "stabilityai/stable-diffusion-xl-base-1.0",
]

def generate_flux_dev(prompt):
    """توليد صورة عبر InferenceClient الرسمي مع fallback تلقائي"""
    if not hf_key:
        raise Exception("مفتاح HF_API_KEY غير موجود في الإعدادات")

    client = InferenceClient(api_key=hf_key)
    last_error = None

    for model_id in HF_MODELS_PRIORITY:
        try:
            st.toast(f"⏳ جاري استخدام {model_id}...")
            image = client.text_to_image(prompt=prompt, model=model_id)
            # image هو PIL.Image — نحوله لـ bytes
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            return "bytes", buf.getvalue()
        except Exception as e:
            last_error = str(e)
            st.toast(f"⚠️ {model_id} غير متاح، أجرّب البديل...")
            continue

    raise Exception(f"فشلت جميع النماذج: {last_error}")


def generate_flux_pro(prompt):
    if not together_key:
        raise Exception("مفتاح TOGETHER_API_KEY غير موجود في الإعدادات")
    headers = {
        "Authorization": f"Bearer {together_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "black-forest-labs/FLUX.1-pro",
        "prompt": prompt,
        "width": 1024, "height": 1024,
        "steps": 28, "n": 1,
        "response_format": "b64_json"
    }
    r = requests.post(
        "https://api.together.xyz/v1/images/generations",
        headers=headers, json=payload, timeout=120
    )
    data = r.json()
    if "error" in data:
        raise Exception(f"خطأ Together AI: {data['error']}")
    img_bytes = base64.b64decode(data["data"][0]["b64_json"])
    return "bytes", img_bytes


def generate_ideogram(prompt):
    if not ideogram_key:
        raise Exception("مفتاح IDEOGRAM_API_KEY غير موجود في الإعدادات")
    headers = {
        "Api-Key": ideogram_key,
        "Content-Type": "application/json"
    }
    payload = {
        "image_request": {
            "prompt": prompt,
            "model": "V_2",
            "magic_prompt_option": "AUTO"
        }
    }
    r = requests.post(
        "https://api.ideogram.ai/generate",
        headers=headers, json=payload, timeout=90
    )
    data = r.json()
    if "data" not in data:
        raise Exception(f"خطأ Ideogram: {data}")
    return "url", data["data"][0]["url"]


def generate_pollinations(prompt, model="flux"):
    """توليد صورة مجاناً بدون أي مفتاح API عبر Pollinations.ai"""
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?model={model}&width=1024&height=1024&nologo=true&enhance=true"
    response = requests.get(url, timeout=90)
    if response.status_code == 200 and response.headers.get("Content-Type","").startswith("image"):
        return "bytes", response.content
    raise Exception(f"فشل Pollinations (كود {response.status_code})")


def generate_image(model_key, prompt):
    if model_key == "poll-flux":
        return generate_pollinations(prompt, model="flux")
    elif model_key == "poll-dalle":
        return generate_pollinations(prompt, model="dall-e-3")
    elif model_key == "poll-turbo":
        return generate_pollinations(prompt, model="turbo")
    elif model_key == "dalle3":
        return generate_dalle(prompt)
    elif model_key == "sdxl":
        return generate_sdxl(prompt)
    elif model_key == "flux-dev":
        return generate_flux_dev(prompt)
    elif model_key == "flux-pro":
        return generate_flux_pro(prompt)
    elif model_key == "ideogram":
        return generate_ideogram(prompt)
    else:
        raise Exception("نموذج غير معروف")


# --- 5. دوال الدردشة ---

GROQ_MODEL_IDS = {
    "groq-llama":   "llama-3.3-70b-versatile",
    "groq-llama8b": "llama-3.1-8b-instant",
    "groq-qwen3":   "qwen/qwen3-32b",
    "groq-llama4":  "meta-llama/llama-4-scout-17b-16e-instruct",
}

OR_MODEL_IDS = {
    "or-auto":     "openrouter/auto",
    "or-claude":   "anthropic/claude-3.5-haiku:free",
    "or-deepseek": "deepseek/deepseek-r1:free",
    "or-llama":    "meta-llama/llama-3.3-70b-instruct:free",
    "or-dsv3":     "deepseek/deepseek-chat-v3-0324:free",
}

GEMINI_MODEL_IDS = {
    "gemini-flash": "models/gemini-2.5-flash",
    "gemini-pro":   "models/gemini-2.5-pro",
}

CLAUDE_MODEL_IDS = {
    "claude-sonnet": "claude-sonnet-4-5",
    "claude-haiku":  "claude-haiku-4-5-20251001",
}

def get_chat_response(user_text, engine, persona, level, file=None):
    model_id = MODEL_MAP[engine]
    system_prompt = f"أنت {persona} بمستوى تفكير {level}. أجب بالعربية دائماً."

    # Claude عبر Anthropic API الرسمي
    if model_id in CLAUDE_MODEL_IDS:
        if not anthropic_key:
            raise Exception("❌ هذا النموذج يحتاج ANTHROPIC_API_KEY — أضفه في Streamlit Secrets أو اختر نموذجاً آخر")
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model=CLAUDE_MODEL_IDS[model_id],
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_text}]
            )
            return msg.content[0].text
        except ImportError:
            raise Exception("❌ مكتبة anthropic غير مثبتة — نفّذ: pip install anthropic")

    # Groq
    if model_id in GROQ_MODEL_IDS:
        if not groq_key:
            raise Exception("❌ هذا النموذج يحتاج GROQ_API_KEY — أضفه في Streamlit Secrets أو اختر نموذجاً آخر")
        if not GROQ_AVAILABLE:
            raise Exception("❌ مكتبة groq غير مثبتة — نفّذ: pip install groq")
        client = Groq(api_key=groq_key)
        r = client.chat.completions.create(
            model=GROQ_MODEL_IDS[model_id],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_text}
            ],
            max_tokens=2048
        )
        return r.choices[0].message.content

    # OpenRouter (نماذج مجانية)
    if model_id in OR_MODEL_IDS:
        if not openrouter_key:
            raise Exception("❌ هذا النموذج يحتاج OPENROUTER_API_KEY — أضفه في Streamlit Secrets أو اختر نموذجاً آخر")
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
        )
        # قائمة fallback لـ Claude المجاني
        claude_free_fallback = [
            "anthropic/claude-3.5-haiku:free",
            "anthropic/claude-3-haiku:free",
            "anthropic/claude-3-opus:free",
            "openrouter/auto",
        ] if model_id == "or-claude" else [OR_MODEL_IDS[model_id]]

        last_err = None
        for model_name in claude_free_fallback:
            try:
                r = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_text}
                    ],
                )
                return r.choices[0].message.content
            except Exception as e:
                last_err = str(e)
                if "404" in last_err or "No endpoints" in last_err:
                    continue
                raise Exception(last_err)
        raise Exception(f"❌ Claude المجاني غير متاح حالياً: {last_err}")

    # DeepSeek محلي
    if model_id == "deepseek-local":
        local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
        r = local_client.chat.completions.create(
            model="deepseek-r1",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_text}
            ]
        )
        return r.choices[0].message.content

    # Gemini (الافتراضي)
    if not api_key:
        raise Exception("مفتاح Gemini غير موجود — اختر نموذجاً آخر أو أضف GEMINI_API_KEY")
    gemini_id = GEMINI_MODEL_IDS.get(model_id, "models/gemini-2.5-flash")
    model = genai.GenerativeModel(gemini_id)
    parts = [f"بصفتك {persona} بمستوى تفكير {level}:\n{user_text}"]
    if file:
        if file.type.startswith("image"):
            parts.append(Image.open(file))
        else:
            parts.append(file.read().decode("utf-8", errors="ignore"))
    return model.generate_content(parts).text


def text_to_speech(text):
    """تحويل النص لصوت — gTTS مجاني"""
    clean = text[:500].replace("*", "").replace("#", "")
    tts = gTTS(text=clean, lang='ar')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp


def speech_to_text(audio_bytes):
    """تحويل الصوت لنص عبر Groq Whisper (مجاني) أو Gemini"""
    if groq_key and GROQ_AVAILABLE:
        try:
            client = Groq(api_key=groq_key)
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"
            result = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=audio_file,
                language="ar",
            )
            return result.text.strip()
        except Exception as e:
            st.toast(f"⚠️ Whisper: {e} — أجرّب Gemini...")

    if api_key:
        try:
            import google.generativeai as genai_mod
            model = genai_mod.GenerativeModel("models/gemini-2.5-flash")
            audio_part = {"mime_type": "audio/wav", "data": audio_bytes}
            result = model.generate_content([
                "حوّل هذا الصوت إلى نص فقط بدون أي تعليق:",
                audio_part
            ])
            return result.text.strip()
        except Exception as e:
            st.toast(f"⚠️ Gemini STT: {e}")

    return None


def stream_chat_response(user_text, engine, persona, level):
    """بث الرد كلمة بكلمة — يدعم Groq وOpenRouter وGemini وClaude"""
    model_id = MODEL_MAP.get(engine, "")
    system_prompt = f"أنت {persona} بمستوى تفكير {level}. أجب بالعربية دائماً."

    # Groq streaming
    if model_id in GROQ_MODEL_IDS and groq_key and GROQ_AVAILABLE:
        client = Groq(api_key=groq_key)
        stream = client.chat.completions.create(
            model=GROQ_MODEL_IDS[model_id],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_text}
            ],
            max_tokens=2048,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
        return

    # OpenRouter streaming
    if model_id in OR_MODEL_IDS and openrouter_key:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
        models_to_try = (
            ["anthropic/claude-3.5-haiku:free", "anthropic/claude-3-haiku:free", "openrouter/auto"]
            if model_id == "or-claude"
            else [OR_MODEL_IDS[model_id]]
        )
        for m in models_to_try:
            try:
                stream = client.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_text}
                    ],
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield delta
                return
            except Exception as e:
                if "404" in str(e) or "No endpoints" in str(e):
                    continue
                raise

    # Claude streaming
    if model_id in CLAUDE_MODEL_IDS and anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            with client.messages.stream(
                model=CLAUDE_MODEL_IDS[model_id],
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": user_text}]
            ) as stream:
                for text in stream.text_stream:
                    yield text
            return
        except ImportError:
            pass

    # Gemini streaming
    if api_key:
        gemini_id = GEMINI_MODEL_IDS.get(model_id, "models/gemini-2.5-flash")
        model = genai.GenerativeModel(gemini_id)
        response = model.generate_content(
            f"بصفتك {persona} بمستوى {level}:\n{user_text}",
            stream=True
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
        return

    raise Exception("لا يوجد نموذج متاح للبث")


def translate_to_english(text):
    prompt = f"Translate the following to English only, no explanation, no quotes:\n{text}"
    if api_key:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        return model.generate_content(prompt).text.strip()
    if groq_key and GROQ_AVAILABLE:
        client = Groq(api_key=groq_key)
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        return r.choices[0].message.content.strip()
    return text



# ═══════════════════════════════════════════════════
# --- وحدة البيانات المالية المباشرة ---
# ═══════════════════════════════════════════════════

@st.cache_data(ttl=60)
def get_stock_data(symbol: str):
    """جلب بيانات السهم من Yahoo Finance (مجاني)"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1mo"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        meta = data["chart"]["result"][0]["meta"]
        quotes = data["chart"]["result"][0]["indicators"]["quote"][0]
        timestamps = data["chart"]["result"][0]["timestamp"]
        return {
            "symbol": symbol.upper(),
            "name": meta.get("shortName", symbol),
            "price": round(meta.get("regularMarketPrice", 0), 2),
            "prev_close": round(meta.get("chartPreviousClose", 0), 2),
            "change": round(meta.get("regularMarketPrice", 0) - meta.get("chartPreviousClose", 0), 2),
            "change_pct": round(((meta.get("regularMarketPrice", 0) - meta.get("chartPreviousClose", 0)) / max(meta.get("chartPreviousClose", 1), 1)) * 100, 2),
            "volume": meta.get("regularMarketVolume", 0),
            "currency": meta.get("currency", "USD"),
            "market_state": meta.get("marketState", ""),
            "closes": [round(c, 2) if c else None for c in quotes.get("close", [])],
            "timestamps": timestamps,
            "high52": round(meta.get("fiftyTwoWeekHigh", 0), 2),
            "low52": round(meta.get("fiftyTwoWeekLow", 0), 2),
        }
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300)
def get_forex_rates(base="USD"):
    """جلب أسعار الصرف (مجاني بلا مفتاح)"""
    try:
        r = requests.get(f"https://api.exchangerate-api.com/v4/latest/{base}", timeout=10)
        data = r.json()
        rates = data.get("rates", {})
        wanted = ["EUR", "GBP", "JPY", "SAR", "AED", "EGP", "TRY", "CHF", "CNY", "CAD"]
        return {
            "base": base,
            "date": data.get("date", ""),
            "rates": {k: round(v, 4) for k, v in rates.items() if k in wanted}
        }
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=120)
def get_crypto_prices():
    """جلب أسعار العملات الرقمية (مجاني)"""
    try:
        coins = "bitcoin,ethereum,binancecoin,ripple,cardano,solana,dogecoin"
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coins}&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
        r = requests.get(url, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=3600)
def get_market_news(query="stock market"):
    """جلب أخبار السوق عبر GNews (مجاني)"""
    try:
        url = f"https://gnews.io/api/v4/search?q={urllib.parse.quote(query)}&lang=ar&max=5&token=free"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("articles", [])
        # بديل مجاني بدون مفتاح
        url2 = f"https://newsdata.io/api/1/news?q={urllib.parse.quote(query)}&language=ar&category=business"
        r2 = requests.get(url2, timeout=10)
        if r2.status_code == 200:
            return r2.json().get("results", [])[:5]
        return []
    except:
        return []


def get_ai_investment_advice(data_context: str, question: str, engine: str, persona: str) -> str:
    """الحصول على تحليل استثماري من الذكاء الاصطناعي"""
    system = """أنت مستشار مالي واستثماري محترف وخبير. تقدم تحليلاً دقيقاً وموضوعياً للأسواق المالية.
تشمل تحليلاتك:
- تقييم المخاطر بوضوح
- التوصيات المبنية على البيانات
- التحذيرات اللازمة
- المقارنة مع بدائل الاستثمار
تذكر دائماً: هذا تحليل للمعلومات وليس توصية استثمارية رسمية. المستخدم مسؤول عن قراراته."""

    full_prompt = f"""البيانات المالية الحالية:
{data_context}

سؤال المستخدم: {question}

قدم تحليلاً استثمارياً شاملاً باللغة العربية يتضمن:
1. تقييم الوضع الحالي
2. نقاط القوة والضعف
3. المخاطر المحتملة
4. توصيات مبنية على البيانات
5. تحذير: هذا تحليل معلوماتي فقط"""

    model_id = MODEL_MAP.get(engine, "gemini-flash")

    if model_id in GROQ_MODEL_IDS and groq_key and GROQ_AVAILABLE:
        client = Groq(api_key=groq_key)
        r = client.chat.completions.create(
            model=GROQ_MODEL_IDS[model_id],
            messages=[{"role": "system", "content": system}, {"role": "user", "content": full_prompt}],
            max_tokens=2048
        )
        return r.choices[0].message.content

    if model_id in CLAUDE_MODEL_IDS and anthropic_key:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)
        msg = client.messages.create(
            model=CLAUDE_MODEL_IDS[model_id], max_tokens=2048,
            system=system, messages=[{"role": "user", "content": full_prompt}]
        )
        return msg.content[0].text

    if api_key:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        return model.generate_content(f"{system}\n\n{full_prompt}").text

    raise Exception("لا يوجد نموذج متاح")


# ═══════════════════════════════════════════════════
# --- قيم افتراضية لتجنب أخطاء المتغيرات ---
audio_record   = None
uploaded_file  = None
engine_choice  = list(MODEL_MAP.keys())[0] if MODEL_MAP else None
persona        = "أهل العلم"
thinking_level = "High"
image_model    = list(IMAGE_MODELS.keys())[0] if IMAGE_MODELS else None
img_style      = "واقعي"
translate_prompt = True
use_streaming  = True
auto_tts       = True
finance_symbol = "AAPL"

# --- 6. القائمة الجانبية ---
with st.sidebar:
    st.header("🎮 مركز التحكم v21")

    mode = st.radio("🔄 وضع العمل:", ["💬 دردشة", "🎨 توليد صور", "📈 مستشار استثماري"])
    st.divider()

    if mode == "💬 دردشة":
        st.subheader("🎤 التسجيل الصوتي")
        audio_record = mic_recorder(
            start_prompt="بدء التسجيل",
            stop_prompt="إرسال الصوت",
            just_once=True,
            key="sidebar_mic"
        )
        use_streaming = st.toggle("⚡ بث مباشر للردود", value=True)
        auto_tts      = st.toggle("🔊 قراءة الرد صوتياً", value=True)
        thinking_level = st.select_slider(
            "🧠 مستوى التفكير:",
            options=["Low", "Medium", "High"],
            value="High"
        )
        persona = st.selectbox("👤 الخبير:", [
            "أهل العلم", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"
        ])
        engine_choice = st.selectbox("🎯 المحرك:", list(MODEL_MAP.keys()))
        selected_key = MODEL_MAP.get(engine_choice, "")
        key_needed = {
            "groq-llama": groq_key, "groq-llama8b": groq_key,
            "groq-qwen3": groq_key, "groq-llama4": groq_key,
            "or-deepseek": openrouter_key, "or-llama": openrouter_key,
            "or-auto": openrouter_key, "or-claude": openrouter_key,
            "or-dsv3": openrouter_key,
            "gemini-flash": api_key, "gemini-pro": api_key,
            "claude-sonnet": anthropic_key, "claude-haiku": anthropic_key,
        }
        if selected_key in key_needed and not key_needed[selected_key]:
            st.warning("⚠️ هذا النموذج يحتاج مفتاح API غير موجود")
        uploaded_file = st.file_uploader(
            "📂 رفع ملف:",
            type=["pdf", "csv", "txt", "jpg", "png", "jpeg"]
        )

    else:
        if IMAGE_MODELS:
            image_model    = st.selectbox("🖼️ نموذج الرسم:", list(IMAGE_MODELS.keys()))
            img_style      = st.selectbox("🎨 الأسلوب:", list(STYLE_MAP.keys()))
            translate_prompt = st.checkbox("🌐 ترجمة الوصف للإنجليزية تلقائياً", value=True)
        else:
            st.error("❌ لا يوجد أي نموذج صور متاح!")

    st.divider()
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.session_state.generated_images = []
        st.rerun()

    with st.expander("🔑 تشخيص المفاتيح"):
        st.write("GEMINI:",      "✅" if api_key        else "❌")
        st.write("ANTHROPIC:",    "✅" if anthropic_key  else "❌")
        st.write("GROQ:",        "✅" if groq_key       else "❌")
        st.write("OPENROUTER:",  "✅" if openrouter_key else "❌")
        st.write("HF:",          "✅" if hf_key         else "❌")
        st.write("OPENAI:",      "✅" if openai_key     else "❌")
        st.write("TOGETHER:",    "✅" if together_key   else "❌")
        st.write("IDEOGRAM:",    "✅" if ideogram_key   else "❌")
        st.write("Pollinations:", "✅ دائماً مجاني")
        if not GROQ_AVAILABLE:
            st.warning("groq غير مثبت — نفّذ: pip install groq")

# --- 7. تهيئة الحالة ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "generated_images" not in st.session_state:
    st.session_state.generated_images = []
if "stock_context" not in st.session_state:
    st.session_state.stock_context = {}
if "forex_context" not in st.session_state:
    st.session_state.forex_context = {}
if "crypto_context" not in st.session_state:
    st.session_state.crypto_context = {}
if "investment_question" not in st.session_state:
    st.session_state.investment_question = ""

# --- 8. وضع الدردشة ---
if mode == "💬 دردشة":
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("اكتب سؤالك أو استخدم الميكروفون...")

    # معالجة الصوت — STT
    user_txt = None
    if audio_record:
        with st.spinner("🎙️ جاري تحويل الصوت لنص..."):
            transcribed = speech_to_text(audio_record["bytes"])
            if transcribed:
                user_txt = transcribed
                st.toast(f"🎙️ فهمت: {transcribed[:60]}...")
            else:
                st.warning("⚠️ لم أتمكن من فهم الصوت، حاول مرة أخرى")
    elif prompt:
        user_txt = prompt

    if user_txt:
        st.session_state.messages.append({"role": "user", "content": user_txt})
        with st.chat_message("user"):
            st.markdown(user_txt)

        with st.chat_message("assistant"):
            try:
                if use_streaming:
                    # البث المباشر كلمة بكلمة
                    reply_placeholder = st.empty()
                    full_reply = ""
                    for chunk in stream_chat_response(
                        user_txt, engine_choice, persona, thinking_level
                    ):
                        full_reply += chunk
                        reply_placeholder.markdown(full_reply + "▌")
                    reply_placeholder.markdown(full_reply)
                    reply = full_reply
                else:
                    with st.spinner("جاري المعالجة..."):
                        reply = get_chat_response(
                            user_txt, engine_choice, persona, thinking_level, uploaded_file
                        )
                        st.markdown(reply)

                # قراءة الرد صوتياً
                if auto_tts and reply:
                    st.audio(text_to_speech(reply), format="audio/mp3", autoplay=True)

                st.session_state.messages.append({"role": "assistant", "content": reply})

            except Exception as e:
                st.error(f"❌ فشل في المعالجة: {e}")

# --- 9. وضع توليد الصور ---
else:
    st.subheader("🎨 توليد الصور بالذكاء الاصطناعي")

    if not IMAGE_MODELS:
        st.error("❌ لا يوجد أي نموذج متاح — أضف مفاتيح API في إعدادات Streamlit")
        st.stop()

    # عرض الصور السابقة
    for img_data in st.session_state.generated_images:
        st.markdown(f"**الوصف:** {img_data['prompt']}")
        if img_data.get("translated"):
            st.caption(f"الوصف المترجم: {img_data['translated']}")
        if img_data["type"] == "url":
            st.image(img_data["data"], use_column_width=True)
        else:
            st.image(img_data["data"], use_column_width=True)
            st.download_button(
                "⬇️ تحميل الصورة",
                data=img_data["data"],
                file_name="generated_image.png",
                mime="image/png",
                key=f"dl_{img_data['prompt'][:20]}"
            )
        st.divider()

    img_prompt = st.chat_input("صف الصورة التي تريدها بالعربية أو الإنجليزية...")

    if img_prompt:
        if not image_model:
            st.error("❌ اختر نموذجاً متاحاً أولاً")
        else:
            with st.spinner("🎨 جاري رسم الصورة... قد يستغرق 30 ثانية"):
                try:
                    final_prompt = img_prompt
                    translated_text = None

                    # ترجمة تلقائية
                    if translate_prompt:
                        translated_text = translate_to_english(img_prompt)
                        final_prompt = translated_text

                    # إضافة الأسلوب
                    style_suffix = STYLE_MAP.get(img_style, "")
                    final_prompt = f"{final_prompt}, {style_suffix}"

                    model_key = IMAGE_MODELS[image_model]
                    result_type, result_data = generate_image(model_key, final_prompt)

                    # حفظ في السجل
                    st.session_state.generated_images.append({
                        "prompt": img_prompt,
                        "translated": translated_text,
                        "type": result_type,
                        "data": result_data
                    })

                    # عرض النتيجة
                    st.markdown(f"**الوصف:** {img_prompt}")
                    if translated_text:
                        st.caption(f"الوصف المترجم: {translated_text}")

                    if result_type == "url":
                        st.image(result_data, use_column_width=True)
                    else:
                        st.image(result_data, use_column_width=True)
                        st.download_button(
                            "⬇️ تحميل الصورة",
                            data=result_data,
                            file_name="generated_image.png",
                            mime="image/png"
                        )

                except Exception as e:
                    err = str(e)
                    if "انتظر" in err or "estimated_time" in err:
                        st.warning(f"⏳ {err}")
                    else:
                        st.error(f"❌ فشل في توليد الصورة: {err}")

# --- 10. وضع المستشار الاستثماري ---
if mode == "📈 مستشار استثماري":
    st.subheader("📈 المستشار الاستثماري الذكي")
    st.caption("بيانات مباشرة من الأسواق العالمية + تحليل بالذكاء الاصطناعي")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 الأسهم", "💱 العملات", "₿ العملات الرقمية", "🤖 المستشار"])

    # ─── تبويب الأسهم ───
    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            symbols_input = st.text_input(
                "رموز الأسهم (مفصولة بفاصلة):",
                value="AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA",
                placeholder="AAPL, TSLA, MSFT..."
            )
        with col2:
            st.write("")
            fetch_btn = st.button("🔄 تحديث", key="fetch_stocks")

        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

        if symbols:
            cols = st.columns(min(len(symbols), 3))
            stock_data_all = {}
            for i, sym in enumerate(symbols[:6]):
                with st.spinner(f"جاري جلب {sym}..."):
                    data = get_stock_data(sym)
                stock_data_all[sym] = data
                with cols[i % 3]:
                    if "error" not in data:
                        arrow = "▲" if data["change"] >= 0 else "▼"
                        color = "🟢" if data["change"] >= 0 else "🔴"
                        st.metric(
                            label=f"{color} {data['symbol']}",
                            value=f"{data['price']} {data['currency']}",
                            delta=f"{arrow} {data['change']} ({data['change_pct']}%)"
                        )
                        with st.expander("تفاصيل"):
                            st.write(f"**الاسم:** {data['name']}")
                            st.write(f"**أعلى 52 أسبوع:** {data['high52']}")
                            st.write(f"**أدنى 52 أسبوع:** {data['low52']}")
                            st.write(f"**الحجم:** {data['volume']:,}")
                            st.write(f"**حالة السوق:** {data['market_state']}")
                            if data["closes"]:
                                valid = [c for c in data["closes"] if c]
                                if valid:
                                    st.line_chart(valid)
                    else:
                        st.error(f"❌ {sym}: {data['error']}")

            # حفظ البيانات للمستشار
            if "stock_context" not in st.session_state:
                st.session_state.stock_context = {}
            st.session_state.stock_context.update(stock_data_all)

    # ─── تبويب العملات ───
    with tab2:
        base_curr = st.selectbox("العملة الأساسية:", ["USD", "EUR", "GBP", "SAR", "AED", "EGP"], key="base_curr")
        with st.spinner("جاري جلب أسعار الصرف..."):
            forex = get_forex_rates(base_curr)

        if "error" not in forex:
            st.success(f"آخر تحديث: {forex['date']}")
            rates = forex["rates"]
            cols = st.columns(4)
            currency_names = {
                "EUR": "يورو 🇪🇺", "GBP": "جنيه إسترليني 🇬🇧",
                "JPY": "ين ياباني 🇯🇵", "SAR": "ريال سعودي 🇸🇦",
                "AED": "درهم إماراتي 🇦🇪", "EGP": "جنيه مصري 🇪🇬",
                "TRY": "ليرة تركية 🇹🇷", "CHF": "فرنك سويسري 🇨🇭",
                "CNY": "يوان صيني 🇨🇳", "CAD": "دولار كندي 🇨🇦",
            }
            for i, (curr, rate) in enumerate(rates.items()):
                with cols[i % 4]:
                    st.metric(
                        label=currency_names.get(curr, curr),
                        value=f"{rate}",
                        delta=None
                    )

            # حاسبة تحويل العملات
            st.divider()
            st.subheader("🔄 حاسبة تحويل العملات")
            c1, c2, c3 = st.columns(3)
            with c1:
                amount = st.number_input("المبلغ:", value=100.0, min_value=0.01)
            with c2:
                target = st.selectbox("إلى:", list(rates.keys()), key="target_curr")
            with c3:
                if target in rates:
                    converted = round(amount * rates[target], 2)
                    st.metric("النتيجة:", f"{converted} {target}")

            st.session_state.forex_context = forex
        else:
            st.error(f"❌ خطأ في جلب العملات: {forex['error']}")

    # ─── تبويب العملات الرقمية ───
    with tab3:
        with st.spinner("جاري جلب أسعار العملات الرقمية..."):
            crypto = get_crypto_prices()

        coin_names = {
            "bitcoin": ("₿ Bitcoin", "BTC"),
            "ethereum": ("Ξ Ethereum", "ETH"),
            "binancecoin": ("BNB", "BNB"),
            "ripple": ("XRP", "XRP"),
            "cardano": ("ADA", "ADA"),
            "solana": ("SOL", "SOL"),
            "dogecoin": ("DOGE 🐕", "DOGE"),
        }

        if "error" not in crypto:
            cols = st.columns(3)
            for i, (coin_id, data) in enumerate(crypto.items()):
                name, symbol = coin_names.get(coin_id, (coin_id, coin_id))
                price = data.get("usd", 0)
                change = data.get("usd_24h_change", 0)
                mcap = data.get("usd_market_cap", 0)
                with cols[i % 3]:
                    st.metric(
                        label=f"{name} ({symbol})",
                        value=f"${price:,.4f}" if price < 1 else f"${price:,.2f}",
                        delta=f"{round(change, 2)}% (24h)"
                    )
                    st.caption(f"القيمة السوقية: ${mcap/1e9:.1f}B")
            st.session_state.crypto_context = crypto
        else:
            st.error(f"❌ {crypto['error']}")

    # ─── تبويب المستشار ───
    with tab4:
        st.subheader("🤖 المستشار الاستثماري الذكي")
        st.info("يستخدم المستشار البيانات المالية المباشرة لتقديم تحليل شامل. اذهب لتبويب الأسهم أو العملات أولاً لتحميل البيانات.")

        # بناء السياق المالي
        context_parts = []
        if st.session_state.get("stock_context"):
            stocks_str = []
            for sym, d in st.session_state.stock_context.items():
                if "error" not in d:
                    stocks_str.append(
                        f"{d['symbol']} ({d['name']}): {d['price']} {d['currency']}, "
                        f"تغيير: {d['change_pct']}%, "
                        f"أعلى 52 أسبوع: {d['high52']}, أدنى: {d['low52']}"
                    )
            if stocks_str:
                context_parts.append("أسعار الأسهم الحالية:\n" + "\n".join(stocks_str))

        if st.session_state.get("forex_context"):
            fx = st.session_state.forex_context
            rates_str = ", ".join([f"{k}: {v}" for k, v in fx["rates"].items()])
            context_parts.append(f"أسعار الصرف ({fx['base']} مقابل): {rates_str}")

        if st.session_state.get("crypto_context"):
            crypto_data = st.session_state.crypto_context
            crypto_str = []
            for coin, d in crypto_data.items():
                if "error" not in d:
                    crypto_str.append(
                        f"{coin}: ${d.get('usd', 0):,.2f} (تغيير 24h: {round(d.get('usd_24h_change', 0), 2)}%)"
                    )
            if crypto_str:
                context_parts.append("أسعار العملات الرقمية:\n" + "\n".join(crypto_str))

        data_context = "\n\n".join(context_parts) if context_parts else "لم يتم تحميل بيانات بعد — يرجى فتح تبويب الأسهم أو العملات أولاً"

        # أسئلة جاهزة
        st.write("**أسئلة جاهزة:**")
        q_cols = st.columns(2)
        preset_questions = [
            "ما هو أفضل سهم للشراء الآن بناءً على البيانات؟",
            "هل العملات الرقمية استثمار جيد الآن؟",
            "حلل مخاطر المحفظة الحالية",
            "ما توقعك لسعر الدولار أمام العملات العربية؟",
            "أيهما أفضل: أسهم التكنولوجيا أم الذهب؟",
            "كيف أوزع استثمار 10,000 دولار بحكمة؟",
        ]
        for i, q in enumerate(preset_questions):
            with q_cols[i % 2]:
                if st.button(q, key=f"preset_{i}", use_container_width=True):
                    st.session_state.investment_question = q

        st.divider()
        investment_q = st.text_area(
            "أو اكتب سؤالك الاستثماري:",
            value=st.session_state.get("investment_question", ""),
            placeholder="مثال: هل يجب أن أشتري أسهم NVDA الآن؟",
            height=100,
            key="investment_input"
        )

        if st.button("🔍 تحليل الآن", type="primary", use_container_width=True):
            if investment_q.strip():
                with st.spinner("🧠 المستشار يحلل البيانات..."):
                    try:
                        advice = get_ai_investment_advice(
                            data_context, investment_q, engine_choice, persona
                        )
                        st.markdown("### 📋 التحليل الاستثماري")
                        st.markdown(advice)
                        st.warning("⚠️ تنبيه: هذا تحليل معلوماتي فقط وليس توصية استثمارية رسمية. استشر خبيراً مالياً معتمداً قبل اتخاذ أي قرار.")
                        if auto_tts:
                            st.audio(text_to_speech(advice[:500]), format="audio/mp3")
                    except Exception as e:
                        st.error(f"❌ {e}")
            else:
                st.warning("اكتب سؤالاً أولاً")
