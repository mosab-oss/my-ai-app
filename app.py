import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from huggingface_hub import InferenceClient
import io, base64, time, requests, urllib.parse
import json, datetime, re
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import fitz
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import openpyxl
    XLSX_AVAILABLE = True
except ImportError:
    XLSX_AVAILABLE = False

# ══════════════════════════════════════════
# 1. الإعدادات
# ══════════════════════════════════════════
st.set_page_config(page_title="منصة مصعب v22", layout="wide", page_icon="🚀")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; background-color: #0e1117; }
    .stSelectbox label, .stSlider label { color: #00ffcc !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════
# 2. مفاتيح API
# ══════════════════════════════════════════
api_key        = st.secrets.get("GEMINI_API_KEY")
openai_key     = st.secrets.get("OPENAI_API_KEY")
hf_key         = st.secrets.get("HF_API_KEY")
together_key   = st.secrets.get("TOGETHER_API_KEY")
ideogram_key   = st.secrets.get("IDEOGRAM_API_KEY")
groq_key       = st.secrets.get("GROQ_API_KEY")
openrouter_key = st.secrets.get("OPENROUTER_API_KEY")
anthropic_key  = st.secrets.get("ANTHROPIC_API_KEY")
tavily_key     = st.secrets.get("TAVILY_API_KEY")
telegram_token = st.secrets.get("TELEGRAM_BOT_TOKEN")
telegram_chat  = st.secrets.get("TELEGRAM_CHAT_ID")

if api_key:
    genai.configure(api_key=api_key)
if not any([api_key, groq_key, anthropic_key, openrouter_key]):
    st.error("يجب وجود مفتاح API واحد على الأقل!")
    st.stop()

# ══════════════════════════════════════════
# 3. نماذج الدردشة
# ══════════════════════════════════════════
ALL_CHAT_MODELS = {
    "Gemini 2.5 Flash":                  ("gemini-flash",  api_key),
    "Gemini 2.5 Pro":                    ("gemini-pro",    api_key),
    "Claude Sonnet 4":                   ("claude-sonnet", anthropic_key),
    "Claude Haiku 4 (سريع)":            ("claude-haiku",  anthropic_key),
    "Claude عبر OpenRouter (مجاني)":    ("or-claude",     openrouter_key),
    "Groq LLaMA 3.3 70B":               ("groq-llama",    groq_key),
    "Groq LLaMA 3.1 8B (سريع)":        ("groq-llama8b",  groq_key),
    "Groq Qwen3 32B":                    ("groq-qwen3",    groq_key),
    "Groq Llama 4 Scout":                ("groq-llama4",   groq_key),
    "OpenRouter Auto (مجاني)":           ("or-auto",       openrouter_key),
    "OpenRouter DeepSeek R1 (مجاني)":   ("or-deepseek",   openrouter_key),
    "OpenRouter Llama 3.3 70B (مجاني)": ("or-llama",      openrouter_key),
    "OpenRouter DeepSeek V3 (مجاني)":   ("or-dsv3",       openrouter_key),
    "DeepSeek R1 (محلي)":               ("deepseek-local",None),
}
MODEL_MAP = {n: k for n, (k, s) in ALL_CHAT_MODELS.items()}

GROQ_MODEL_IDS = {
    "groq-llama":   "llama-3.3-70b-versatile",
    "groq-llama8b": "llama-3.1-8b-instant",
    "groq-qwen3":   "qwen/qwen3-32b",
    "groq-llama4":  "meta-llama/llama-4-scout-17b-16e-instruct",
}
OR_MODEL_IDS = {
    "or-auto":     "openrouter/auto",
    "or-claude":   "anthropic/claude-3.5-haiku:free",
    "or-deepseek": "deepseek/deepseek-r1-distill-llama-70b:free",
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

# ══════════════════════════════════════════
# 4. نماذج الصور
# ══════════════════════════════════════════
ALL_IMAGE_MODELS = {
    "Pollinations FLUX (مجاني)":   ("poll-flux",  True),
    "Pollinations DALL-E (مجاني)": ("poll-dalle", True),
    "Pollinations Turbo (مجاني)":  ("poll-turbo", True),
    "Flux-Schnell (HuggingFace)":  ("flux-dev",   hf_key),
    "Stable Diffusion XL":         ("sdxl",       hf_key),
    "DALL-E 3 (OpenAI)":          ("dalle3",      openai_key),
}
IMAGE_MODELS = {n: k for n, (k, s) in ALL_IMAGE_MODELS.items() if s}
STYLE_MAP = {
    "واقعي":      "photorealistic, ultra detailed, high quality",
    "كرتوني":     "cartoon style, colorful, flat design",
    "زيتي":       "oil painting style, textured, classical",
    "خيال علمي":  "sci-fi, futuristic, neon lights",
    "انيمي":      "anime style, manga illustration",
    "رسم بقلم":   "pencil sketch, detailed line art",
    "مائي":       "watercolor painting, soft colors",
}

# ══════════════════════════════════════════
# 5. الذاكرة الدائمة
# ══════════════════════════════════════════
MEMORY_FILE = "/tmp/mosab_memory.json"

def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"conversations": {}, "alerts": [], "analytics": {"total_messages": 0, "model_usage": {}, "daily": {}}}

def save_memory(data):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def save_conversation(conv_id, messages):
    mem = load_memory()
    mem["conversations"][conv_id] = {
        "messages": messages,
        "updated": datetime.datetime.now().isoformat(),
        "title": messages[0]["content"][:50] if messages else "محادثة جديدة"
    }
    save_memory(mem)

def log_analytics(model_name):
    mem = load_memory()
    mem["analytics"]["total_messages"] = mem["analytics"].get("total_messages", 0) + 1
    usage = mem["analytics"].get("model_usage", {})
    usage[model_name] = usage.get(model_name, 0) + 1
    mem["analytics"]["model_usage"] = usage
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    daily = mem["analytics"].get("daily", {})
    daily[today] = daily.get(today, 0) + 1
    mem["analytics"]["daily"] = daily
    save_memory(mem)

# ══════════════════════════════════════════
# 6. البحث في الإنترنت
# ══════════════════════════════════════════
def web_search(query, max_results=5):
    results = []
    if tavily_key:
        try:
            r = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": tavily_key, "query": query, "max_results": max_results},
                timeout=10
            )
            if r.status_code == 200:
                for item in r.json().get("results", []):
                    results.append({"title": item.get("title",""), "url": item.get("url",""), "snippet": item.get("content","")[:300]})
                return results
        except:
            pass

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(
            "https://api.duckduckgo.com/?q=" + urllib.parse.quote(query) + "&format=json&no_redirect=1",
            headers=headers, timeout=8
        )
        data = r.json()
        abstract = data.get("AbstractText", "")
        if abstract:
            results.append({"title": data.get("Heading", query), "url": data.get("AbstractURL",""), "snippet": abstract[:400]})
        for topic in data.get("RelatedTopics", [])[:max_results-1]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({"title": topic.get("Text","")[:60], "url": topic.get("FirstURL",""), "snippet": topic.get("Text","")[:300]})
    except:
        pass

    if not results:
        try:
            r = requests.get(
                "https://ar.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(query),
                timeout=8
            )
            if r.status_code == 200:
                d = r.json()
                results.append({"title": d.get("title",""), "url": d.get("content_urls",{}).get("desktop",{}).get("page",""), "snippet": d.get("extract","")[:400]})
        except:
            pass

    return results


def search_and_answer(query, engine, persona):
    results = web_search(query)
    context = "\n\n".join([
        "المصدر " + str(i+1) + ": " + r["title"] + "\n" + r["snippet"]
        for i, r in enumerate(results)
    ]) if results else "لم تُوجد نتائج."

    prompt = "بناء على نتائج البحث التالية، اجب على السؤال:\n\n" + context + "\n\nالسؤال: " + query + "\n\nاجب بالعربية."
    model_id = MODEL_MAP.get(engine, "gemini-flash")

    if model_id in GROQ_MODEL_IDS and groq_key and GROQ_AVAILABLE:
        client = Groq(api_key=groq_key)
        r = client.chat.completions.create(
            model=GROQ_MODEL_IDS[model_id],
            messages=[{"role": "user", "content": prompt}], max_tokens=2048
        )
        return r.choices[0].message.content, results

    if api_key:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        return model.generate_content(prompt).text, results

    if openrouter_key:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
        r = client.chat.completions.create(model="openrouter/auto", messages=[{"role":"user","content":prompt}])
        return r.choices[0].message.content, results

    return "لا نموذج متاح", results

# ══════════════════════════════════════════
# 7. تحليل الوثائق
# ══════════════════════════════════════════
def extract_text_from_file(uploaded_file):
    name = uploaded_file.name.lower()
    content = uploaded_file.read()
    if name.endswith(".txt") or name.endswith(".csv"):
        return content.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        if PDF_AVAILABLE:
            doc = fitz.open(stream=content, filetype="pdf")
            return "\n".join([page.get_text() for page in doc])
        return "[يحتاج: pip install pymupdf]"
    if name.endswith(".docx"):
        if DOCX_AVAILABLE:
            d = docx.Document(io.BytesIO(content))
            return "\n".join([p.text for p in d.paragraphs])
        return "[يحتاج: pip install python-docx]"
    if name.endswith((".xlsx",".xls")):
        if XLSX_AVAILABLE:
            wb = openpyxl.load_workbook(io.BytesIO(content))
            lines = []
            for sheet in wb.worksheets:
                lines.append("=== ورقة: " + sheet.title + " ===")
                for row in sheet.iter_rows(values_only=True):
                    row_text = " | ".join([str(c) if c is not None else "" for c in row])
                    if row_text.strip(" |"):
                        lines.append(row_text)
            return "\n".join(lines)
        return "[يحتاج: pip install openpyxl]"
    return content.decode("utf-8", errors="ignore")


def analyze_document(text, question, engine):
    truncated = text[:8000] + ("...[مقتطع]" if len(text) > 8000 else "")
    prompt = "تحليل الوثيقة:\n" + truncated + "\n\nالمهمة: " + question + "\n\nاجب بالعربية."
    model_id = MODEL_MAP.get(engine, "gemini-flash")

    if model_id in GROQ_MODEL_IDS and groq_key and GROQ_AVAILABLE:
        client = Groq(api_key=groq_key)
        r = client.chat.completions.create(
            model=GROQ_MODEL_IDS[model_id],
            messages=[{"role":"user","content":prompt}], max_tokens=2048
        )
        return r.choices[0].message.content
    if api_key:
        return genai.GenerativeModel("models/gemini-2.5-flash").generate_content(prompt).text
    if openrouter_key:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
        r = client.chat.completions.create(model="openrouter/auto", messages=[{"role":"user","content":prompt}])
        return r.choices[0].message.content
    raise Exception("لا نموذج متاح")

# ══════════════════════════════════════════
# 8. تحليل الصور (Vision)
# ══════════════════════════════════════════
def analyze_image_with_ai(image_bytes, question, engine):
    model_id = MODEL_MAP.get(engine, "gemini-flash")
    img_b64 = base64.b64encode(image_bytes).decode()
    q = question or "صف هذه الصورة بالتفصيل"

    if api_key:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        img_part = {"mime_type": "image/jpeg", "data": image_bytes}
        return model.generate_content([q, img_part]).text

    if model_id in CLAUDE_MODEL_IDS and anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            msg = client.messages.create(
                model=CLAUDE_MODEL_IDS[model_id], max_tokens=1024,
                messages=[{"role":"user","content":[
                    {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":img_b64}},
                    {"type":"text","text":q}
                ]}]
            )
            return msg.content[0].text
        except ImportError:
            pass

    if openrouter_key:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
        r = client.chat.completions.create(
            model="meta-llama/llama-4-scout:free",
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+img_b64}},
                {"type":"text","text":q}
            ]}]
        )
        return r.choices[0].message.content

    return "لا يوجد نموذج Vision متاح"

# ══════════════════════════════════════════
# 9. تنبيهات Telegram
# ══════════════════════════════════════════
def send_telegram(message):
    if not telegram_token or not telegram_chat:
        return False
    try:
        r = requests.post(
            "https://api.telegram.org/bot" + telegram_token + "/sendMessage",
            json={"chat_id": telegram_chat, "text": message, "parse_mode": "Markdown"},
            timeout=10
        )
        return r.status_code == 200
    except:
        return False


def check_price_alerts():
    mem = load_memory()
    alerts = mem.get("alerts", [])
    if not alerts:
        return
    triggered = []
    for alert in alerts:
        try:
            if alert["type"] == "crypto":
                r = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price?ids=" + alert["coin"] + "&vs_currencies=usd",
                    timeout=8
                )
                price = r.json().get(alert["coin"], {}).get("usd", 0)
            else:
                r = requests.get(
                    "https://query1.finance.yahoo.com/v8/finance/chart/" + alert["symbol"] + "?interval=1d&range=1d",
                    headers={"User-Agent": "Mozilla/5.0"}, timeout=8
                )
                price = r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"]

            cond_met = (alert["condition"] == "above" and price >= alert["target"]) or \
                       (alert["condition"] == "below" and price <= alert["target"])
            if cond_met:
                msg = "تنبيه سعر: " + alert.get("name", "") + " السعر الحالي: $" + str(round(price, 2)) + " الهدف: $" + str(alert["target"])
                send_telegram(msg)
                st.toast("🔔 " + msg)
                triggered.append(alert)
        except:
            pass
    mem["alerts"] = [a for a in alerts if a not in triggered]
    save_memory(mem)

# ══════════════════════════════════════════
# 10. Multi-Agent
# ══════════════════════════════════════════
def multi_agent_response(user_text, persona):
    steps = []
    agent1_result = ""
    agent2_result = ""

    if groq_key and GROQ_AVAILABLE:
        with st.status("الوكيل 1 (Groq): يبحث..."):
            search_results = web_search(user_text, max_results=3)
            context = "\n".join(["- " + r["title"] + ": " + r["snippet"] for r in search_results])
            client = Groq(api_key=groq_key)
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user","content":"لخص: " + context + "\nالسؤال: " + user_text}],
                max_tokens=800
            )
            agent1_result = r.choices[0].message.content
            steps.append("**Groq (باحث):**\n" + agent1_result)

    if api_key:
        with st.status("الوكيل 2 (Gemini): يحلل..."):
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            agent2_result = model.generate_content("حلل واضف رؤى:\n" + (agent1_result or user_text)).text
            steps.append("**Gemini (محلل):**\n" + agent2_result)

    final_result = ""
    if anthropic_key:
        with st.status("الوكيل 3 (Claude): يكتب التقرير..."):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_key)
                combined = "البحث:\n" + agent1_result + "\n\nالتحليل:\n" + agent2_result
                msg = client.messages.create(
                    model="claude-haiku-4-5-20251001", max_tokens=1500,
                    system="انت " + persona + ". اكتب تقريرا نهائيا منظما بالعربية.",
                    messages=[{"role":"user","content":"اكتب تقريرا عن: " + user_text + "\n\n" + combined}]
                )
                final_result = msg.content[0].text
            except:
                final_result = agent2_result or agent1_result
    else:
        final_result = agent2_result or agent1_result

    with st.expander("تفاصيل عمل الوكلاء"):
        for step in steps:
            st.markdown(step)
            st.divider()

    return final_result

# ══════════════════════════════════════════
# 11. البيانات المالية
# ══════════════════════════════════════════
@st.cache_data(ttl=60)
def get_stock_data(symbol):
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?interval=1d&range=1mo"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        meta = data["chart"]["result"][0]["meta"]
        quotes = data["chart"]["result"][0]["indicators"]["quote"][0]
        price = meta.get("regularMarketPrice", 0)
        prev = meta.get("chartPreviousClose", 0)
        return {
            "symbol": symbol.upper(),
            "name": meta.get("shortName", symbol),
            "price": round(price, 2),
            "change": round(price - prev, 2),
            "change_pct": round(((price - prev) / max(prev, 1)) * 100, 2),
            "volume": meta.get("regularMarketVolume", 0),
            "currency": meta.get("currency", "USD"),
            "market_state": meta.get("marketState", ""),
            "closes": [round(c, 2) if c else None for c in quotes.get("close", [])],
            "high52": round(meta.get("fiftyTwoWeekHigh", 0), 2),
            "low52": round(meta.get("fiftyTwoWeekLow", 0), 2),
        }
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300)
def get_forex_rates(base="USD"):
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/" + base, timeout=10)
        data = r.json()
        wanted = ["EUR","GBP","JPY","SAR","AED","EGP","TRY","CHF","CNY","CAD"]
        return {"base": base, "date": data.get("date",""), "rates": {k: round(v,4) for k,v in data.get("rates",{}).items() if k in wanted}}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=120)
def get_crypto_prices():
    try:
        coins = "bitcoin,ethereum,binancecoin,ripple,cardano,solana,dogecoin"
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=" + coins + "&vs_currencies=usd&include_24hr_change=true&include_market_cap=true",
            timeout=10
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ══════════════════════════════════════════
# 12. دوال الدردشة
# ══════════════════════════════════════════

def is_quota_error(e):
    """تحقق إذا كان الخطأ بسبب تجاوز الحصة"""
    err = str(e).lower()
    return any(x in err for x in ["quota", "rate limit", "429", "resource exhausted", "exceeded"])


def fallback_response(user_text, sys_p):
    """تبديل تلقائي للنموذج عند تجاوز الحصة — يجرب بالترتيب"""
    # 1. Groq أولاً (مجاني وسريع وبلا حد يومي عملي)
    if groq_key and GROQ_AVAILABLE:
        try:
            c = Groq(api_key=groq_key)
            r = c.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"system","content":sys_p},{"role":"user","content":user_text}],
                max_tokens=2048
            )
            st.toast("🔄 تم التبديل تلقائياً لـ Groq LLaMA")
            return r.choices[0].message.content
        except:
            pass

    # 2. OpenRouter (مجاني)
    if openrouter_key:
        try:
            c = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
            r = c.chat.completions.create(
                model="openrouter/auto",
                messages=[{"role":"system","content":sys_p},{"role":"user","content":user_text}]
            )
            st.toast("🔄 تم التبديل تلقائياً لـ OpenRouter")
            return r.choices[0].message.content
        except:
            pass

    # 3. Claude (مدفوع لكن موثوق)
    if anthropic_key:
        try:
            import anthropic
            c = anthropic.Anthropic(api_key=anthropic_key)
            msg = c.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=2048,
                system=sys_p, messages=[{"role":"user","content":user_text}]
            )
            st.toast("🔄 تم التبديل تلقائياً لـ Claude Haiku")
            return msg.content[0].text
        except:
            pass

    raise Exception("❌ تجاوزت حصة Gemini اليومية (20 طلب) ولا يوجد بديل متاح. أضف GROQ_API_KEY أو OPENROUTER_API_KEY.")


def get_chat_response(user_text, engine, persona, level, file=None):
    model_id = MODEL_MAP.get(engine, "gemini-flash")
    sys_p = "انت " + persona + " بمستوى " + level + ". اجب بالعربية."

    if model_id in CLAUDE_MODEL_IDS:
        if not anthropic_key:
            raise Exception("يحتاج ANTHROPIC_API_KEY")
        try:
            import anthropic
            c = anthropic.Anthropic(api_key=anthropic_key)
            msg = c.messages.create(model=CLAUDE_MODEL_IDS[model_id], max_tokens=2048, system=sys_p, messages=[{"role":"user","content":user_text}])
            return msg.content[0].text
        except ImportError:
            raise Exception("pip install anthropic")

    if model_id in GROQ_MODEL_IDS:
        if not groq_key: raise Exception("يحتاج GROQ_API_KEY")
        c = Groq(api_key=groq_key)
        r = c.chat.completions.create(model=GROQ_MODEL_IDS[model_id], messages=[{"role":"system","content":sys_p},{"role":"user","content":user_text}], max_tokens=2048)
        return r.choices[0].message.content

    if model_id in OR_MODEL_IDS:
        if not openrouter_key: raise Exception("يحتاج OPENROUTER_API_KEY")
        c = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
        models_to_try = ["anthropic/claude-3.5-haiku:free","openrouter/auto"] if model_id == "or-claude" else [OR_MODEL_IDS[model_id]]
        for m in models_to_try:
            try:
                r = c.chat.completions.create(model=m, messages=[{"role":"system","content":sys_p},{"role":"user","content":user_text}])
                return r.choices[0].message.content
            except Exception as e:
                if "404" in str(e) or "No endpoints" in str(e): continue
                raise

    if model_id == "deepseek-local":
        c = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
        r = c.chat.completions.create(model="deepseek-r1", messages=[{"role":"system","content":sys_p},{"role":"user","content":user_text}])
        return r.choices[0].message.content

    # Gemini مع fallback تلقائي عند تجاوز الحصة
    if not api_key:
        return fallback_response(user_text, sys_p)

    try:
        gemini_id = GEMINI_MODEL_IDS.get(model_id, "models/gemini-2.5-flash")
        model = genai.GenerativeModel(gemini_id)
        parts = ["بصفتك " + persona + " بمستوى " + level + ":\n" + user_text]
        if file:
            if file.type.startswith("image"):
                parts.append(Image.open(file))
            else:
                parts.append(file.read().decode("utf-8", errors="ignore"))
        return model.generate_content(parts).text
    except Exception as e:
        if is_quota_error(e):
            st.warning("⚠️ تجاوزت حصة Gemini اليومية (20 طلب/يوم) — يتم التبديل تلقائياً...")
            return fallback_response(user_text, sys_p)
        raise


def stream_chat_response(user_text, engine, persona, level):
    model_id = MODEL_MAP.get(engine, "")
    sys_p = "انت " + persona + " بمستوى " + level + ". اجب بالعربية."

    if model_id in GROQ_MODEL_IDS and groq_key and GROQ_AVAILABLE:
        c = Groq(api_key=groq_key)
        stream = c.chat.completions.create(model=GROQ_MODEL_IDS[model_id], messages=[{"role":"system","content":sys_p},{"role":"user","content":user_text}], max_tokens=2048, stream=True)
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta: yield delta
        return

    if model_id in OR_MODEL_IDS and openrouter_key:
        c = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
        models_to_try = ["anthropic/claude-3.5-haiku:free","openrouter/auto"] if model_id == "or-claude" else [OR_MODEL_IDS[model_id]]
        for m in models_to_try:
            try:
                stream = c.chat.completions.create(model=m, messages=[{"role":"system","content":sys_p},{"role":"user","content":user_text}], stream=True)
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta: yield delta
                return
            except Exception as e:
                if "404" in str(e) or "No endpoints" in str(e): continue
                raise

    if model_id in CLAUDE_MODEL_IDS and anthropic_key:
        try:
            import anthropic
            c = anthropic.Anthropic(api_key=anthropic_key)
            with c.messages.stream(model=CLAUDE_MODEL_IDS[model_id], max_tokens=2048, system=sys_p, messages=[{"role":"user","content":user_text}]) as stream:
                for text in stream.text_stream:
                    yield text
            return
        except ImportError:
            pass

    if api_key:
        try:
            gemini_id = GEMINI_MODEL_IDS.get(model_id, "models/gemini-2.5-flash")
            model = genai.GenerativeModel(gemini_id)
            response = model.generate_content("بصفتك " + persona + " بمستوى " + level + ":\n" + user_text, stream=True)
            for chunk in response:
                if chunk.text: yield chunk.text
            return
        except Exception as e:
            if is_quota_error(e):
                st.warning("⚠️ تجاوزت حصة Gemini — يتم التبديل تلقائياً...")
                yield fallback_response(user_text, sys_p)
                return
            raise

    yield fallback_response(user_text, sys_p)


def text_to_speech(text):
    clean = text[:500].replace("*","").replace("#","")
    tts = gTTS(text=clean, lang="ar")
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp


def speech_to_text(audio_bytes):
    if groq_key and GROQ_AVAILABLE:
        try:
            c = Groq(api_key=groq_key)
            af = io.BytesIO(audio_bytes)
            af.name = "audio.wav"
            result = c.audio.transcriptions.create(model="whisper-large-v3-turbo", file=af, language="ar")
            return result.text.strip()
        except Exception as e:
            st.toast("Whisper: " + str(e))
    if api_key:
        try:
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            return model.generate_content(["حول هذا الصوت لنص:", {"mime_type":"audio/wav","data":audio_bytes}]).text.strip()
        except:
            pass
    return None


def translate_to_english(text):
    prompt = "Translate to English only:\n" + text
    # Groq أولاً لتوفير حصة Gemini
    if groq_key and GROQ_AVAILABLE:
        try:
            r = Groq(api_key=groq_key).chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role":"user","content":prompt}], max_tokens=200
            )
            return r.choices[0].message.content.strip()
        except:
            pass
    if api_key:
        try:
            return genai.GenerativeModel("models/gemini-2.5-flash").generate_content(prompt).text.strip()
        except Exception as e:
            if is_quota_error(e):
                return text  # أعد النص كما هو إذا تجاوزت الحصة
            raise
    return text

# ══════════════════════════════════════════
# 13. توليد الصور
# ══════════════════════════════════════════
def generate_pollinations(prompt, model="flux"):
    encoded = urllib.parse.quote(prompt)
    url = "https://image.pollinations.ai/prompt/" + encoded + "?model=" + model + "&width=1024&height=1024&nologo=true&enhance=true"
    r = requests.get(url, timeout=90)
    if r.status_code == 200 and r.headers.get("Content-Type","").startswith("image"):
        return "bytes", r.content
    raise Exception("Pollinations: " + str(r.status_code))


def generate_dalle(prompt):
    if not openai_key: raise Exception("يحتاج OPENAI_API_KEY")
    c = OpenAI(api_key=openai_key)
    r = c.images.generate(model="dall-e-3", prompt=prompt, size="1024x1024", n=1)
    return "url", r.data[0].url


def generate_hf(prompt, model_id):
    if not hf_key: raise Exception("يحتاج HF_API_KEY")
    c = InferenceClient(api_key=hf_key)
    image = c.text_to_image(prompt=prompt, model=model_id)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return "bytes", buf.getvalue()


def generate_image(model_key, prompt):
    if model_key == "poll-flux":  return generate_pollinations(prompt, "flux")
    if model_key == "poll-dalle": return generate_pollinations(prompt, "dall-e-3")
    if model_key == "poll-turbo": return generate_pollinations(prompt, "turbo")
    if model_key == "dalle3":     return generate_dalle(prompt)
    if model_key == "flux-dev":   return generate_hf(prompt, "black-forest-labs/FLUX.1-schnell")
    if model_key == "sdxl":       return generate_hf(prompt, "stabilityai/stable-diffusion-xl-base-1.0")
    raise Exception("نموذج غير معروف")

# ══════════════════════════════════════════
# 14. تهيئة الحالة
# ══════════════════════════════════════════
defaults = {
    "messages": [], "generated_images": [],
    "stock_context": {}, "forex_context": {}, "crypto_context": {},
    "investment_question": "",
    "conv_id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
    "doc_text": "", "doc_question": "", "search_query": "", "vision_q": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

check_price_alerts()

# ══════════════════════════════════════════
# 15. القائمة الجانبية
# ══════════════════════════════════════════
audio_record = None
uploaded_file = None
engine_choice = list(MODEL_MAP.keys())[0]
persona = "مساعد ذكي"
thinking_level = "High"
image_model = list(IMAGE_MODELS.keys())[0] if IMAGE_MODELS else None
img_style = "واقعي"
translate_prompt = True
use_streaming = True
auto_tts = True
enable_multiagent = False

with st.sidebar:
    st.header("🚀 مركز التحكم v22")
    mode = st.radio("الوضع:", [
        "💬 دردشة",
        "🌐 بحث في الإنترنت",
        "📄 تحليل وثائق",
        "🖼️ تحليل صور",
        "🎨 توليد صور",
        "📈 مستشار استثماري",
        "🔔 تنبيهات الأسعار",
        "📊 الاحصائيات",
    ])
    st.divider()

    if mode == "💬 دردشة":
        audio_record    = mic_recorder(start_prompt="تسجيل", stop_prompt="ارسال", just_once=True, key="mic")
        use_streaming   = st.toggle("بث مباشر", value=True)
        auto_tts        = st.toggle("قراءة صوتية", value=True)
        enable_multiagent = st.toggle("Multi-Agent", value=False)
        thinking_level  = st.select_slider("مستوى التفكير:", ["Low","Medium","High"], value="High")
        persona         = st.selectbox("الشخصية:", ["مساعد ذكي","اهل العلم","خبير برمجة","محلل مالي","معلم","كاتب"])
        engine_choice   = st.selectbox("النموذج:", list(MODEL_MAP.keys()))
        uploaded_file   = st.file_uploader("ملف:", type=["pdf","docx","txt","csv","xlsx","jpg","png"])

    elif mode in ["🌐 بحث في الإنترنت","📄 تحليل وثائق","🖼️ تحليل صور","📈 مستشار استثماري","🔔 تنبيهات الأسعار"]:
        engine_choice = st.selectbox("النموذج:", list(MODEL_MAP.keys()))
        auto_tts = st.toggle("قراءة صوتية", value=False)

    elif mode == "🎨 توليد صور":
        if IMAGE_MODELS:
            image_model     = st.selectbox("نموذج الرسم:", list(IMAGE_MODELS.keys()))
            img_style       = st.selectbox("الاسلوب:", list(STYLE_MAP.keys()))
            translate_prompt = st.checkbox("ترجمة تلقائية", value=True)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("مسح", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conv_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            st.rerun()
    with c2:
        if st.button("حفظ", use_container_width=True):
            save_conversation(st.session_state.conv_id, st.session_state.messages)
            st.toast("المحادثة محفوظة!")

    with st.expander("المفاتيح"):
        for name, key in [("GEMINI",api_key),("ANTHROPIC",anthropic_key),("GROQ",groq_key),
                          ("OPENROUTER",openrouter_key),("HF",hf_key),("OPENAI",openai_key),
                          ("TAVILY",tavily_key),("TELEGRAM",telegram_token)]:
            st.write(name + ": " + ("✅" if key else "❌"))
        st.write("Pollinations: ✅ مجاني")

    with st.expander("المحادثات المحفوظة"):
        mem = load_memory()
        convs = mem.get("conversations", {})
        for cid, conv in list(convs.items())[-5:]:
            if st.button(conv["title"][:30], key="conv_"+cid):
                st.session_state.messages = conv["messages"]
                st.session_state.conv_id = cid
                st.rerun()

# ══════════════════════════════════════════
# 16. الواجهات
# ══════════════════════════════════════════

if mode == "💬 دردشة":
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("اكتب سؤالك...")
    user_txt = None

    if audio_record:
        with st.spinner("تحويل الصوت..."):
            transcribed = speech_to_text(audio_record["bytes"])
            if transcribed:
                user_txt = transcribed
                st.toast("فهمت: " + transcribed[:50])
            else:
                st.warning("لم افهم الصوت")
    elif prompt:
        user_txt = prompt

    if user_txt:
        st.session_state.messages.append({"role":"user","content":user_txt})
        with st.chat_message("user"):
            st.markdown(user_txt)
        with st.chat_message("assistant"):
            try:
                if enable_multiagent:
                    reply = multi_agent_response(user_txt, persona)
                    st.markdown(reply)
                elif use_streaming:
                    ph = st.empty()
                    full_reply = ""
                    for chunk in stream_chat_response(user_txt, engine_choice, persona, thinking_level):
                        full_reply += chunk
                        ph.markdown(full_reply + "▌")
                    ph.markdown(full_reply)
                    reply = full_reply
                else:
                    with st.spinner("جاري المعالجة..."):
                        reply = get_chat_response(user_txt, engine_choice, persona, thinking_level, uploaded_file)
                        st.markdown(reply)

                if auto_tts and reply:
                    st.audio(text_to_speech(reply), format="audio/mp3", autoplay=True)
                st.session_state.messages.append({"role":"assistant","content":reply})
                log_analytics(engine_choice)
            except Exception as e:
                st.error("❌ " + str(e))

elif mode == "🌐 بحث في الإنترنت":
    st.subheader("🌐 البحث في الإنترنت")
    quick = ["اخر اخبار الذكاء الاصطناعي","اسعار الذهب اليوم","افضل لغات البرمجة 2025","اخبار الاسواق المالية"]
    cols = st.columns(2)
    for i, q in enumerate(quick):
        with cols[i%2]:
            if st.button(q, key="qs_"+str(i), use_container_width=True):
                st.session_state.search_query = q

    search_q = st.text_input("ابحث:", value=st.session_state.get("search_query",""), placeholder="اكتب موضوع البحث...")
    if st.button("بحث الآن", type="primary") and search_q:
        with st.spinner("جاري البحث..."):
            try:
                answer, results = search_and_answer(search_q, engine_choice, persona)
                st.markdown("### النتيجة")
                st.markdown(answer)
                if results:
                    with st.expander("المصادر"):
                        for r in results:
                            st.markdown("**" + r["title"] + "**")
                            st.caption(r["url"])
                            st.write(r["snippet"])
                            st.divider()
                log_analytics(engine_choice)
            except Exception as e:
                st.error("❌ " + str(e))

elif mode == "📄 تحليل وثائق":
    st.subheader("📄 تحليل الوثائق")
    st.info("PDF: " + ("✅" if PDF_AVAILABLE else "❌ pip install pymupdf") +
            " | Word: " + ("✅" if DOCX_AVAILABLE else "❌ pip install python-docx") +
            " | Excel: " + ("✅" if XLSX_AVAILABLE else "❌ pip install openpyxl"))

    doc_file = st.file_uploader("ارفع ملفك:", type=["pdf","docx","txt","csv","xlsx","xls"])
    if doc_file:
        with st.spinner("قراءة الملف..."):
            text = extract_text_from_file(doc_file)
            st.session_state.doc_text = text
            st.success("تم قراءة " + str(len(text)) + " حرف")
            with st.expander("معاينة"):
                st.text(text[:2000] + ("..." if len(text) > 2000 else ""))

    if st.session_state.doc_text:
        st.divider()
        quick_tasks = ["لخص هذا الملف","ما اهم المعلومات؟","استخرج الارقام والاحصائيات","ما التوصيات المذكورة؟"]
        t_cols = st.columns(2)
        for i, task in enumerate(quick_tasks):
            with t_cols[i%2]:
                if st.button(task, key="task_"+str(i), use_container_width=True):
                    st.session_state.doc_question = task

        doc_q = st.text_area("سؤالك:", value=st.session_state.get("doc_question",""), height=80)
        if st.button("تحليل", type="primary") and doc_q:
            with st.spinner("جاري التحليل..."):
                try:
                    result = analyze_document(st.session_state.doc_text, doc_q, engine_choice)
                    st.markdown("### نتيجة التحليل")
                    st.markdown(result)
                    log_analytics(engine_choice)
                except Exception as e:
                    st.error("❌ " + str(e))

elif mode == "🖼️ تحليل صور":
    st.subheader("🖼️ تحليل الصور")
    img_file = st.file_uploader("ارفع صورة:", type=["jpg","jpeg","png","webp"])
    if img_file:
        img_bytes = img_file.read()
        st.image(img_bytes, use_column_width=True)
        quick_vision = ["صف هذه الصورة","ما النص في الصورة؟","حلل هذا الرسم البياني","ما المشكلة في هذا الكود؟"]
        v_cols = st.columns(2)
        for i, q in enumerate(quick_vision):
            with v_cols[i%2]:
                if st.button(q, key="vision_"+str(i), use_container_width=True):
                    st.session_state.vision_q = q

        vision_q = st.text_input("سؤالك:", value=st.session_state.get("vision_q",""))
        if st.button("تحليل الصورة", type="primary"):
            with st.spinner("جاري التحليل..."):
                try:
                    result = analyze_image_with_ai(img_bytes, vision_q or "صف هذه الصورة", engine_choice)
                    st.markdown("### التحليل")
                    st.markdown(result)
                    if auto_tts:
                        st.audio(text_to_speech(result[:400]), format="audio/mp3")
                    log_analytics(engine_choice)
                except Exception as e:
                    st.error("❌ " + str(e))

elif mode == "🎨 توليد صور":
    st.subheader("🎨 توليد الصور")
    for img_data in st.session_state.generated_images:
        st.markdown("**الوصف:** " + img_data["prompt"])
        if img_data["type"] == "url":
            st.image(img_data["data"], use_column_width=True)
        else:
            st.image(img_data["data"], use_column_width=True)
            st.download_button("تحميل", data=img_data["data"], file_name="image.png", mime="image/png", key="dl_"+img_data["prompt"][:10])
        st.divider()

    img_prompt = st.chat_input("صف الصورة...")
    if img_prompt:
        if not image_model:
            st.error("لا يوجد نموذج")
        else:
            with st.spinner("جاري الرسم..."):
                try:
                    fp = translate_to_english(img_prompt) if translate_prompt else img_prompt
                    fp += ", " + STYLE_MAP.get(img_style, "")
                    rtype, rdata = generate_image(IMAGE_MODELS[image_model], fp)
                    st.session_state.generated_images.append({"prompt": img_prompt, "type": rtype, "data": rdata})
                    st.rerun()
                except Exception as e:
                    st.error("❌ " + str(e))

elif mode == "📈 مستشار استثماري":
    st.subheader("📈 المستشار الاستثماري الذكي")
    tab1, tab2, tab3, tab4 = st.tabs(["الاسهم","العملات","الكريبتو","المستشار"])

    with tab1:
        symbols_input = st.text_input("رموز الاسهم:", value="AAPL, MSFT, GOOGL, NVDA, TSLA")
        symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
        if st.button("تحديث الاسهم"):
            cols = st.columns(min(len(symbols),3))
            for i, sym in enumerate(symbols[:6]):
                data = get_stock_data(sym)
                st.session_state.stock_context[sym] = data
                with cols[i%3]:
                    if "error" not in data:
                        arrow = "▲" if data["change"] >= 0 else "▼"
                        color = "🟢" if data["change"] >= 0 else "🔴"
                        st.metric(color + " " + data["symbol"], str(data["price"]) + " " + data["currency"], arrow + " " + str(data["change_pct"]) + "%")
                        valid_closes = [c for c in data["closes"] if c]
                        if valid_closes:
                            st.line_chart(valid_closes)
                    else:
                        st.error("❌ " + sym + ": " + data["error"])

    with tab2:
        base = st.selectbox("العملة الاساسية:", ["USD","EUR","GBP","SAR","AED"])
        forex = get_forex_rates(base)
        if "error" not in forex:
            st.success("آخر تحديث: " + forex["date"])
            cols = st.columns(4)
            for i, (curr, rate) in enumerate(forex["rates"].items()):
                with cols[i%4]:
                    st.metric(curr, str(rate))
            st.divider()
            amount = st.number_input("تحويل:", value=100.0)
            target = st.selectbox("الى:", list(forex["rates"].keys()))
            if target in forex["rates"]:
                st.metric("النتيجة:", str(round(amount * forex["rates"][target], 2)) + " " + target)
            st.session_state.forex_context = forex

    with tab3:
        crypto = get_crypto_prices()
        if "error" not in crypto:
            cols = st.columns(3)
            names = {"bitcoin":"₿ Bitcoin","ethereum":"Ξ Ethereum","binancecoin":"BNB","ripple":"XRP","cardano":"ADA","solana":"SOL","dogecoin":"DOGE"}
            for i, (coin, d) in enumerate(crypto.items()):
                price = d.get("usd", 0)
                change = d.get("usd_24h_change", 0)
                with cols[i%3]:
                    st.metric(names.get(coin, coin), "$" + str(round(price, 2)), str(round(change, 2)) + "% (24h)")
            st.session_state.crypto_context = crypto

    with tab4:
        context_parts = []
        if st.session_state.stock_context:
            lines = [s + ": " + str(d["price"]) + " " + d.get("currency","USD") + " (" + str(d["change_pct"]) + "%)"
                     for s, d in st.session_state.stock_context.items() if "error" not in d]
            if lines: context_parts.append("الاسهم:\n" + "\n".join(lines))
        if st.session_state.get("forex_context"):
            fx = st.session_state.forex_context
            context_parts.append("اسعار الصرف (" + fx["base"] + "): " + ", ".join(k+"="+str(v) for k,v in fx["rates"].items()))
        if st.session_state.get("crypto_context"):
            lines = [c + ": $" + str(round(d.get("usd",0),2)) for c,d in st.session_state.crypto_context.items()]
            context_parts.append("الكريبتو:\n" + "\n".join(lines))
        data_context = "\n\n".join(context_parts) or "لم تحمل بيانات بعد"

        presets = ["افضل سهم للشراء؟","هل الكريبتو استثمار جيد؟","كيف اوزع 10000$؟","حلل مخاطر المحفظة","توقعات الدولار؟"]
        p_cols = st.columns(2)
        for i, q in enumerate(presets):
            with p_cols[i%2]:
                if st.button(q, key="inv_"+str(i), use_container_width=True):
                    st.session_state.investment_question = q

        inv_q = st.text_area("سؤالك الاستثماري:", value=st.session_state.investment_question, height=80)
        if st.button("تحليل استثماري", type="primary") and inv_q:
            with st.spinner("المستشار يحلل..."):
                try:
                    prompt = "انت مستشار مالي محترف. البيانات:\n" + data_context + "\n\nالسؤال: " + inv_q + "\n\nقدم تحليلا شاملا بالعربية مع التحذير ان هذا للمعلومات فقط."
                    reply = get_chat_response(prompt, engine_choice, "محلل مالي", "High")
                    st.markdown(reply)
                    st.warning("تنبيه: هذا تحليل معلوماتي فقط - استشر خبيرا ماليا")
                    if auto_tts:
                        st.audio(text_to_speech(reply[:400]), format="audio/mp3")
                except Exception as e:
                    st.error("❌ " + str(e))

elif mode == "🔔 تنبيهات الأسعار":
    st.subheader("🔔 تنبيهات الأسعار التلقائية")
    if not telegram_token:
        st.warning("اضف TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID في Secrets لاستقبال اشعارات Telegram")

    mem = load_memory()
    alerts = mem.get("alerts", [])

    with st.form("add_alert"):
        a_cols = st.columns(4)
        with a_cols[0]: alert_type = st.selectbox("النوع:", ["stock","crypto"])
        with a_cols[1]: alert_sym = st.text_input("الرمز:", placeholder="AAPL او bitcoin")
        with a_cols[2]: alert_cond = st.selectbox("الشرط:", ["above","below"])
        with a_cols[3]: alert_target = st.number_input("السعر ($):", min_value=0.0, value=100.0)
        if st.form_submit_button("اضافة التنبيه", use_container_width=True):
            new_alert = {
                "type": alert_type,
                "symbol": alert_sym.upper() if alert_type == "stock" else alert_sym.lower(),
                "coin": alert_sym.lower(), "name": alert_sym.upper(),
                "condition": alert_cond, "target": alert_target,
                "created": datetime.datetime.now().isoformat()
            }
            alerts.append(new_alert)
            mem["alerts"] = alerts
            save_memory(mem)
            st.success("تم اضافة التنبيه!")
            st.rerun()

    st.divider()
    st.write("التنبيهات النشطة (" + str(len(alerts)) + "):")
    for i, alert in enumerate(alerts):
        c1, c2 = st.columns([4,1])
        with c1:
            cond_txt = "يتجاوز" if alert["condition"] == "above" else "ينزل دون"
            st.write("🔔 **" + alert["name"] + "** — " + cond_txt + " **$" + str(alert["target"]) + "**")
        with c2:
            if st.button("حذف", key="del_"+str(i)):
                alerts.pop(i)
                mem["alerts"] = alerts
                save_memory(mem)
                st.rerun()

    if st.button("فحص التنبيهات الآن"):
        check_price_alerts()
        st.success("تم الفحص")

elif mode == "📊 الاحصائيات":
    st.subheader("📊 احصائيات الاستخدام")
    mem = load_memory()
    analytics = mem.get("analytics", {})

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("اجمالي الرسائل", analytics.get("total_messages", 0))
    with c2: st.metric("محادثات محفوظة", len(mem.get("conversations", {})))
    with c3: st.metric("تنبيهات نشطة", len(mem.get("alerts", [])))

    st.divider()
    model_usage = analytics.get("model_usage", {})
    if model_usage:
        st.write("**استخدام النماذج:**")
        total = sum(model_usage.values())
        for model_name, count in sorted(model_usage.items(), key=lambda x: x[1], reverse=True):
            pct = int((count / total) * 100) if total > 0 else 0
            st.write(model_name + ": " + str(count) + " رسالة (" + str(pct) + "%)")
            st.progress(pct / 100)

    daily = analytics.get("daily", {})
    if daily:
        st.divider()
        st.write("**الاستخدام اليومي (آخر 7 ايام):**")
        for day, count in sorted(daily.items())[-7:]:
            st.write(day + ": " + ("█" * min(count, 30)) + " (" + str(count) + ")")

    if st.button("مسح الاحصائيات"):
        mem["analytics"] = {"total_messages": 0, "model_usage": {}, "daily": {}}
        save_memory(mem)
        st.success("تم المسح")
        st.rerun()
