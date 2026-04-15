import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, requests, base64
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder

st.set_page_config(page_title="منصة مصعب v18", layout="wide", page_icon="🎤")
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; background-color: #111; }
    .stSelectbox label, .stSlider label { color: #00ffcc !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- مفاتيح API ---
api_key = st.secrets.get("GEMINI_API_KEY")
openai_key = st.secrets.get("OPENAI_API_KEY")
hf_key = st.secrets.get("HF_API_KEY")
stability_key = st.secrets.get("STABILITY_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

MODEL_MAP = {
    "Gemini 2.5 Flash": "models/gemini-2.5-flash",
    "Gemini 2.5 Pro":   "models/gemini-2.5-pro-preview-03-25",
    "DeepSeek R1 (محلي)": "deepseek-r1",
}

# نماذج الرسم
IMAGE_MODELS = {
    "DALL·E 3 (OpenAI)":         "dalle3",
    "Stable Diffusion XL":        "sdxl",
    "Flux-Dev (Hugging Face)":    "flux-dev",
    "Flux-Pro (API)":             "flux-pro",
    "Ideogram v2":                "ideogram",
}

# --- دوال توليد الصور ---

def generate_dalle(prompt):
    client = OpenAI(api_key=openai_key)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url

def generate_sdxl(prompt):
    """Stable Diffusion XL عبر Hugging Face"""
    headers = {"Authorization": f"Bearer {hf_key}"}
    payload = {"inputs": prompt}
    response = requests.post(
        "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
        headers=headers,
        json=payload,
        timeout=60
    )
    if response.status_code == 200:
        return response.content  # bytes
    raise Exception(f"خطأ: {response.text}")

def generate_flux_dev(prompt):
    """Flux-Dev عبر Hugging Face"""
    headers = {"Authorization": f"Bearer {hf_key}"}
    payload = {"inputs": prompt}
    response = requests.post(
        "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev",
        headers=headers,
        json=payload,
        timeout=90
    )
    if response.status_code == 200:
        return response.content
    raise Exception(f"خطأ: {response.text}")

def generate_flux_pro(prompt):
    """Flux-Pro عبر Together AI"""
    headers = {
        "Authorization": f"Bearer {st.secrets.get('TOGETHER_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "black-forest-labs/FLUX.1-pro",
        "prompt": prompt,
        "width": 1024, "height": 1024,
        "steps": 28, "n": 1,
        "response_format": "b64_json"
    }
    r = requests.post("https://api.together.xyz/v1/images/generations",
                      headers=headers, json=payload, timeout=120)
    data = r.json()
    img_bytes = base64.b64decode(data["data"][0]["b64_json"])
    return img_bytes

def generate_ideogram(prompt):
    """Ideogram v2 عبر API"""
    headers = {
        "Api-Key": st.secrets.get("IDEOGRAM_API_KEY"),
        "Content-Type": "application/json"
    }
    payload = {
        "image_request": {
            "prompt": prompt,
            "model": "V_2",
            "magic_prompt_option": "AUTO"
        }
    }
    r = requests.post("https://api.ideogram.ai/generate",
                      headers=headers, json=payload, timeout=90)
    return r.json()["data"][0]["url"]

def generate_image(model_key, prompt):
    """دالة مركزية لتوليد الصور"""
    if model_key == "dalle3":
        return "url", generate_dalle(prompt)
    elif model_key == "sdxl":
        return "bytes", generate_sdxl(prompt)
    elif model_key == "flux-dev":
        return "bytes", generate_flux_dev(prompt)
    elif model_key == "flux-pro":
        return "bytes", generate_flux_pro(prompt)
    elif model_key == "ideogram":
        return "url", generate_ideogram(prompt)

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("🎮 مركز التحكم v18")

    mode = st.radio("🔄 وضع العمل:", ["💬 دردشة", "🎨 توليد صور"])

    st.divider()

    if mode == "💬 دردشة":
        st.subheader("🎤 التسجيل الصوتي")
        audio_record = mic_recorder(
            start_prompt="بدء التسجيل",
            stop_prompt="إرسال الصوت",
            just_once=True, key='sidebar_mic'
        )
        thinking_level = st.select_slider(
            "🧠 مستوى التفكير:",
            options=["Low", "Medium", "High"], value="High"
        )
        persona = st.selectbox("👤 الخبير:", [
            "أهل العلم", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"
        ])
        engine_choice = st.selectbox("🎯 المحرك:", list(MODEL_MAP.keys()))
        uploaded_file = st.file_uploader(
            "📂 رفع ملف:",
            type=["pdf", "csv", "txt", "jpg", "png", "jpeg"]
        )
    else:
        audio_record = None
        uploaded_file = None
        image_model = st.selectbox("🖼️ نموذج الرسم:", list(IMAGE_MODELS.keys()))
        img_size = st.selectbox("📐 الحجم:", ["1024×1024", "1792×1024", "1024×1792"])
        img_style = st.selectbox("🎨 الأسلوب:", [
            "واقعي", "كرتوني", "زيتي", "خيال علمي",
            "أنيمي", "رسم بالقلم", "مائي"
        ])
        translate_prompt = st.checkbox("🌐 ترجمة الوصف للإنجليزية تلقائياً", value=True)

    st.divider()
    if st.button("🗑️ مسح"):
        st.session_state.messages = []
        st.session_state.generated_images = []
        st.rerun()

# --- دوال مساعدة ---
def get_chat_response(user_text, engine, persona, level, file=None):
    model_id = MODEL_MAP[engine]
    if "deepseek" in model_id:
        local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
        r = local_client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": f"أنت {persona} بمستوى {level}. أجب بالعربية."},
                {"role": "user", "content": user_text}
            ]
        )
        return r.choices[0].message.content

    model = genai.GenerativeModel(model_id)
    parts = [f"بصفتك {persona} بمستوى {level}:\n{user_text}"]
    if file:
        if file.type.startswith("image"):
            parts.append(Image.open(file))
        else:
            parts.append(file.read().decode("utf-8", errors="ignore"))
    return model.generate_content(parts).text

def text_to_speech(text):
    tts = gTTS(text=text[:400].replace("*","").replace("#",""), lang='ar')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp

def translate_to_english(text):
    """ترجمة النص للإنجليزية باستخدام Gemini"""
    model = genai.GenerativeModel("models/gemini-2.5-flash")
    r = model.generate_content(f"Translate to English only, no explanation:\n{text}")
    return r.text.strip()

# --- الواجهة الرئيسية ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

# وضع الدردشة
if mode == "💬 دردشة":
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("اكتب سؤالك...")

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
                    st.audio(text_to_speech(reply), format='audio/mp3')
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                except Exception as e:
                    st.error(f"❌ {e}")

# وضع توليد الصور
else:
    st.subheader("🎨 توليد الصور بالذكاء الاصطناعي")

    # عرض الصور السابقة
    for img_data in st.session_state.generated_images:
        st.markdown(f"**الوصف:** {img_data['prompt']}")
        if img_data["type"] == "url":
            st.image(img_data["data"], use_column_width=True)
        else:
            st.image(img_data["data"], use_column_width=True)
        st.divider()

    img_prompt = st.chat_input("صف الصورة التي تريدها بالعربية أو الإنجليزية...")

    if img_prompt:
        with st.spinner("جاري رسم الصورة..."):
            try:
                final_prompt = img_prompt
                style_map = {
                    "واقعي": "photorealistic, high quality",
                    "كرتوني": "cartoon style, colorful",
                    "زيتي": "oil painting style",
                    "خيال علمي": "sci-fi, futuristic",
                    "أنيمي": "anime style",
                    "رسم بالقلم": "pencil sketch, detailed",
                    "مائي": "watercolor painting"
                }

                # ترجمة تلقائية إذا كان الخيار مفعّلاً
                if translate_prompt and api_key:
                    final_prompt = translate_to_english(img_prompt)

                # إضافة الأسلوب للوصف
                final_prompt = f"{final_prompt}, {style_map.get(img_style, '')}"

                model_key = IMAGE_MODELS[image_model]
                result_type, result_data = generate_image(model_key, final_prompt)

                st.session_state.generated_images.append({
                    "prompt": img_prompt,
                    "type": result_type,
                    "data": result_data
                })

                st.markdown(f"**الوصف:** {img_prompt}")
                if translate_prompt:
                    st.caption(f"الوصف المترجم: {final_prompt}")

                if result_type == "url":
                    st.image(result_data, use_column_width=True)
                else:
                    st.image(result_data, use_column_width=True)

                # زر التحميل
                if result_type == "bytes":
                    st.download_button(
                        "⬇️ تحميل الصورة",
                        data=result_data,
                        file_name="generated_image.png",
                        mime="image/png"
                    )

            except Exception as e:
                st.error(f"❌ فشل في توليد الصورة: {e}")
