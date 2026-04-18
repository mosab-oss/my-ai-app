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
st.set_page_config(page_title="منصة مصعب v19", layout="wide", page_icon="🎤")
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

if api_key:
    genai.configure(api_key=api_key)
elif not groq_key:
    st.error("⚠️ يجب وجود GEMINI_API_KEY أو GROQ_API_KEY على الأقل!")
    st.stop()

# --- 3. قوائم النماذج ---
ALL_CHAT_MODELS = {
    "Gemini 2.5 Flash":                  ("gemini-flash",   api_key),
    "Gemini 2.5 Pro":                    ("gemini-pro",     api_key),
    "Groq LLaMA 3.3 70B":                ("groq-llama",     groq_key),
    "Groq LLaMA 3.1 8B (سريع)":         ("groq-llama8b",   groq_key),
    "Groq Qwen3 32B":                    ("groq-qwen3",     groq_key),
    "Groq Llama 4 Scout":                ("groq-llama4",    groq_key),
    "OpenRouter Auto (أفضل مجاني)":      ("or-auto",        openrouter_key),
    "OpenRouter DeepSeek R1 (مجاني)":    ("or-deepseek",    openrouter_key),
    "OpenRouter Llama 3.3 70B (مجاني)":  ("or-llama",       openrouter_key),
    "OpenRouter DeepSeek V3 (مجاني)":    ("or-dsv3",        openrouter_key),
    "DeepSeek R1 (محلي)":                ("deepseek-local", None),
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
    "or-deepseek": "deepseek/deepseek-r1:free",
    "or-llama":    "meta-llama/llama-3.3-70b-instruct:free",
    "or-dsv3":     "deepseek/deepseek-chat-v3-0324:free",
}

GEMINI_MODEL_IDS = {
    "gemini-flash": "models/gemini-2.5-flash",
    "gemini-pro":   "models/gemini-2.5-pro",
}

def get_chat_response(user_text, engine, persona, level, file=None):
    model_id = MODEL_MAP[engine]
    system_prompt = f"أنت {persona} بمستوى تفكير {level}. أجب بالعربية دائماً."

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
        r = client.chat.completions.create(
            model=OR_MODEL_IDS[model_id],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_text}
            ],
        )
        return r.choices[0].message.content

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
    clean = text[:400].replace("*", "").replace("#", "")
    tts = gTTS(text=clean, lang='ar')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp


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


# --- قيم افتراضية لتجنب أخطاء المتغيرات ---
audio_record   = None
uploaded_file  = None
engine_choice  = list(MODEL_MAP.keys())[0] if MODEL_MAP else None
persona        = "أهل العلم"
thinking_level = "High"
image_model    = list(IMAGE_MODELS.keys())[0] if IMAGE_MODELS else None
img_style      = "واقعي"
translate_prompt = True

# --- 6. القائمة الجانبية ---
with st.sidebar:
    st.header("🎮 مركز التحكم v19")

    mode = st.radio("🔄 وضع العمل:", ["💬 دردشة", "🎨 توليد صور"])
    st.divider()

    if mode == "💬 دردشة":
        st.subheader("🎤 التسجيل الصوتي")
        audio_record = mic_recorder(
            start_prompt="بدء التسجيل",
            stop_prompt="إرسال الصوت",
            just_once=True,
            key="sidebar_mic"
        )
        thinking_level = st.select_slider(
            "🧠 مستوى التفكير:",
            options=["Low", "Medium", "High"],
            value="High"
        )
        persona = st.selectbox("👤 الخبير:", [
            "أهل العلم", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"
        ])
        engine_choice = st.selectbox("🎯 المحرك:", list(MODEL_MAP.keys()))
        # تحذير إذا النموذج المختار يحتاج مفتاح غير موجود
        selected_key = MODEL_MAP.get(engine_choice, "")
        key_needed = {
            "groq-llama": groq_key, "groq-mixtral": groq_key, "groq-deepseek": groq_key,
            "or-deepseek": openrouter_key, "or-qwen": openrouter_key,
            "gemini-flash": api_key, "gemini-pro": api_key,
        }
        if selected_key in key_needed and not key_needed[selected_key]:
            st.warning(f"⚠️ هذا النموذج يحتاج مفتاح API غير موجود")
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

# --- 8. وضع الدردشة ---
if mode == "💬 دردشة":
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("اكتب سؤالك أو استخدم الميكروفون...")

    if prompt or audio_record:
        user_txt = prompt if prompt else "🎤 [رسالة صوتية]"
        st.session_state.messages.append({"role": "user", "content": user_txt})
        with st.chat_message("user"):
            st.markdown(user_txt)
        with st.chat_message("assistant"):
            with st.spinner("جاري المعالجة..."):
                try:
                    reply = get_chat_response(
                        user_txt, engine_choice, persona, thinking_level, uploaded_file
                    )
                    st.markdown(reply)
                    st.audio(text_to_speech(reply), format="audio/mp3")
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
