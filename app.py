import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والواجهة (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.11.9", layout="wide", page_icon="🎤")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; background-color: #111; }
    .stSelectbox label, .stSlider label { color: #00ffcc !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# الربط المحلي ومحركات جوجل
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية الشاملة (كل شيء في مكان واحد) ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.11.9")
    
    # أداة الميكروفون (المغرفون) - الآن في القائمة
    st.subheader("🎤 المغرفون (للتكلم)")
    audio_record = mic_recorder(
        start_prompt="بدء التسجيل", 
        stop_prompt="إرسال الصوت", 
        just_once=True, 
        key='sidebar_mic'
    )
    
    st.divider()

    # مستوى التفكير
    thinking_level = st.select_slider(
        "🧠 مستوى التفكير:", 
        options=["Low", "Medium", "High"], 
        value="High"
    )
    
    # اختيار الشخصية (المعرفون)
    persona = st.selectbox(
        "👤 اختيار الخبير:", 
        ["المعرفون (أهل العلم)", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"]
    )
    
    st.divider()
    
    # اختيار المحرك
    engine_choice = st.selectbox(
        "🎯 المحرك:",
        ["Gemini 2.5 Flash", "Gemini 3 Pro", "DeepSeek R1"]
    )
    
    # رفع الملفات
    uploaded_file = st.file_uploader("📂 رفع الملفات:", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    st.divider()
    
    # فحص الموديلات النشطة
    st.subheader("🛠️ الصيانة")
    if st.button("🔍 فحص الموديلات النشطة"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.info("الموديلات المتاحة:")
            st.code("\n".join(models))
        except Exception as e: st.error(f"خطأ: {e}")

# --- 3. واجهة الدردشة الرئيسية ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("اكتب سؤالك هنا أو استخدم المغرفون من القائمة الجانبية...")

# معالجة المدخلات
if prompt or audio_record or uploaded_file:
    user_txt = prompt if prompt else "🎤 [تم إرسال أمر صوتي]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            model_map = {"Gemini 3 Pro": "models/gemini-3-pro-preview", "Gemini 2.5 Flash": "models/gemini-2.5-flash"}
            model = genai.GenerativeModel(model_map.get(engine_choice, "models/gemini-2.5-flash"))
            
            # بناء الطلب
            full_prompt = f"بصفتك {persona} وبمستوى تفكير {thinking_level}: {user_txt}"
            content_parts = [full_prompt]
            
            if uploaded_file:
                if uploaded_file.type.startswith("image"):
                    content_parts.append(Image.open(uploaded_file))
                else:
                    content_parts.append(uploaded_file.read().decode())
            
            if audio_record:
                content_parts.append({"mime_type": "audio/wav", "data": audio_record['bytes']})

            response = model.generate_content(content_parts)
            st.markdown(response.text)
            
            # نطق الرد آلياً
            tts = gTTS(text=response.text[:300], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3')
            
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e: st.error(f"فشل في المعالجة: {e}")
