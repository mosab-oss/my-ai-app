import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الهوية والواجهة (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.12.0", layout="wide", page_icon="🎙️")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    /* تنسيق أزرار القائمة الجانبية لتكون واضحة */
    [data-testid="stSidebar"] { background-color: #0e1117; }
    .stButton button { width: 100%; border-radius: 10px; font-weight: bold; }
    .mic-box { border: 2px solid #ff4b4b; padding: 10px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# الربط التقني
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية: مركز التحكم الموحد ---
with st.sidebar:
    st.title("🎮 مركز التحكم")
    st.write(f"**الإصدار:** v16.12.0")
    
    # أ. قسم المغرفون (الميكروفون) - في القائمة الجانبية كما طلبت
    st.markdown('<div class="mic-box">', unsafe_allow_html=True)
    st.subheader("🎤 المغرفون")
    audio_record = mic_recorder(
        start_prompt="بدء التكلم", 
        stop_prompt="إرسال الصوت", 
        just_once=True, 
        key='sidebar_mic'
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ب. مستوى التفكير (Thinking)
    thinking_level = st.select_slider(
        "🧠 مستوى التفكير:", 
        options=["Low", "Medium", "High"], 
        value="High"
    )

    # ج. الشخصية (المعرفون)
    persona = st.selectbox(
        "👤 اختر الشخصية:", 
        ["المعرفون (أهل العلم)", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"]
    )
    
    st.divider()
    
    # د. المحرك ورفع الملفات
    engine_choice = st.selectbox("🎯 المحرك:", ["Gemini 2.5 Flash", "Gemini 3 Pro", "DeepSeek R1"])
    uploaded_file = st.file_uploader("📂 رفع الملفات:", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    st.divider()
    
    # هـ. أدوات الصيانة (فحص الموديلات)
    st.subheader("🛠️ أدوات الصيانة")
    if st.button("🔍 فحص الموديلات النشطة", type="primary"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.info("النماذج المتاحة لحسابك:")
            st.code("\n".join(models))
        except Exception as e: st.error(f"خطأ في الفحص: {e}")

    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- 3. واجهة الدردشة الرئيسية ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("اكتب سؤالك هنا...")

# المعالجة الذكية للمدخلات (نص، صوت، أو ملف)
if prompt or audio_record or uploaded_file:
    user_txt = prompt if prompt else "🎤 [رسالة صوتية عبر المغرفون]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            model_map = {"Gemini 3 Pro": "models/gemini-3-pro-preview", "Gemini 2.5 Flash": "models/gemini-2.5-flash"}
            model = genai.GenerativeModel(model_map.get(engine_choice, "models/gemini-2.5-flash"))
            
            # دمج التعليمات
            full_prompt = f"بصفتك {persona} وبمستوى تفكير {thinking_level}: {user_txt}"
            parts = [full_prompt]
            
            if uploaded_file:
                if uploaded_file.type.startswith("image"): parts.append(Image.open(uploaded_file))
                else: parts.append(uploaded_file.read().decode())
            
            if audio_record:
                parts.append({"mime_type": "audio/wav", "data": audio_record['bytes']})

            response = model.generate_content(parts)
            st.markdown(response.text)
            
            # الرد الصوتي الآلي (تكلم المنصة)
            tts = gTTS(text=response.text[:300], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3')
            
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e: st.error(f"حدث خطأ: {e}")
