import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder

# --- 1. الإعدادات ---
st.set_page_config(page_title="منصة مصعب v17", layout="wide", page_icon="🎤")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    section[data-testid="stSidebar"] { 
        direction: rtl; text-align: right; background-color: #111; 
    }
    .stSelectbox label, .stSlider label { color: #00ffcc !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. تهيئة النماذج ---
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ مفتاح GEMINI_API_KEY غير موجود في الإعدادات!")
    st.stop()

MODEL_MAP = {
    "Gemini 2.5 Flash": "models/gemini-2.5-flash",
    "Gemini 2.5 Pro":   "models/gemini-2.5-pro-preview-03-25",
    "DeepSeek R1 (محلي)": "deepseek-r1",
}

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.header("🎮 مركز التحكم v17")

    st.subheader("🎤 التسجيل الصوتي")
    audio_record = mic_recorder(
        start_prompt="بدء التسجيل",
        stop_prompt="إرسال الصوت",
        just_once=True,
        key='sidebar_mic'
    )

    st.divider()

    thinking_level = st.select_slider(
        "🧠 مستوى التفكير:",
        options=["Low", "Medium", "High"],
        value="High"
    )

    persona = st.selectbox(
        "👤 اختيار الخبير:",
        ["أهل العلم", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"]
    )

    engine_choice = st.selectbox("🎯 المحرك:", list(MODEL_MAP.keys()))

    uploaded_file = st.file_uploader(
        "📂 رفع ملف:",
        type=["pdf", "csv", "txt", "jpg", "png", "jpeg"]
    )

    st.divider()

    # فحص النماذج المتاحة
    if st.button("🔍 فحص النماذج المتاحة"):
        try:
            models = [
                m.name for m in genai.list_models()
                if 'generateContent' in m.supported_generation_methods
            ]
            st.code("\n".join(models))
        except Exception as e:
            st.error(f"خطأ: {e}")

    # زر مسح المحادثة
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- 4. واجهة الدردشة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("اكتب سؤالك أو استخدم الميكروفون...")

# --- 5. معالجة المدخلات ---
def get_response(user_text, engine, persona, level, file=None):
    """دالة مركزية للحصول على الرد"""
    model_id = MODEL_MAP[engine]

    # DeepSeek عبر LM Studio المحلي
    if "deepseek" in model_id:
        local_client = OpenAI(
            base_url="http://127.0.0.1:1234/v1",
            api_key="lm-studio"
        )
        system_prompt = f"أنت {persona} وتفكر بمستوى {level}. أجب بالعربية."
        response = local_client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ]
        )
        return response.choices[0].message.content

    # Gemini
    model = genai.GenerativeModel(model_id)
    full_prompt = f"بصفتك {persona} وبمستوى تفكير {level}:\n{user_text}"
    content_parts = [full_prompt]

    if file:
        if file.type.startswith("image"):
            content_parts.append(Image.open(file))
        else:
            try:
                content_parts.append(file.read().decode("utf-8"))
            except UnicodeDecodeError:
                content_parts.append("(ملف غير قابل للقراءة كنص)")

    response = model.generate_content(content_parts)
    return response.text


def text_to_speech(text):
    """تحويل النص إلى صوت"""
    clean_text = text[:400].replace("*", "").replace("#", "")
    tts = gTTS(text=clean_text, lang='ar')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    return audio_fp


# المعالجة الرئيسية
if prompt or audio_record:
    user_txt = prompt if prompt else "🎤 [رسالة صوتية - يرجى الرد بشكل عام]"

    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"):
        st.markdown(user_txt)

    with st.chat_message("assistant"):
        with st.spinner("جاري المعالجة..."):
            try:
                reply = get_response(
                    user_txt, engine_choice,
                    persona, thinking_level, uploaded_file
                )
                st.markdown(reply)

                # نطق الرد
                audio_fp = text_to_speech(reply)
                st.audio(audio_fp, format='audio/mp3')

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply
                })
            except Exception as e:
                st.error(f"❌ فشل في المعالجة: {e}")
