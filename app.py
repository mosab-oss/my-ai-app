import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والواجهة (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.11.8", layout="wide", page_icon="🎤")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    /* تمييز الميكروفون بلون واضح */
    .stButton button { background-color: #ff4b4b; color: white; border-radius: 20px; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# الربط المحلي ومحركات جوجل
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية (كل الأدوات التي سألت عنها) ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.11.8")
    
    # خبير المعرفة (الذين يعلمون)
    persona = st.selectbox(
        "👤 اختر الشخصية:", 
        ["المعرفون (خبير العلم)", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"]
    )

    # مستوى التفكير (Thinking) - عاد لمكانه
    thinking_level = st.select_slider(
        "🧠 مستوى التفكير:", 
        options=["Low", "Medium", "High"], 
        value="High"
    )
    
    st.divider()
    
    # اختيار المحرك
    engine_choice = st.selectbox(
        "🎯 المحرك المستخدم:",
        ["Gemini 2.5 Flash", "Gemini 3 Pro", "Gemma 3 27B", "DeepSeek R1"]
    )
    
    # رفع الملفات (موجود وشغال)
    uploaded_file = st.file_uploader("📂 ارفع ملف (صورة/PDF):", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    st.divider()
    
    # زر فحص الموديلات النشطة
    st.subheader("🛠️ الصيانة")
    if st.button("🔍 فحص الموديلات النشطة"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.info("الموديلات المتاحة:")
            st.code("\n".join(models))
        except Exception as e: st.error(f"خطأ: {e}")

# --- 3. قسم الميكروفون (المغرفون) في الواجهة الرئيسية ---
st.title("🎤 منصة التكلم الصوتي")
st.write("استخدم **الميكروفون** للتحدث مباشرة مع النظام:")

# أداة الميكروفون (المغرفون كما تسميه)
audio_record = mic_recorder(
    start_prompt="🎤 اضغط هنا للتكلم (المغرفون)", 
    stop_prompt="🛑 توقف وأرسل", 
    just_once=True, 
    key='main_mic'
)

# --- 4. معالجة البيانات ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("أو اكتب سؤالك هنا...")

# التحقق من وجود إدخال صوتي أو نصي أو ملف
if prompt or audio_record or uploaded_file:
    # إذا كان هناك تسجيل صوتي، نحتاج لتحويله لنص (أو إرساله كملف لجيمناي)
    user_txt = prompt if prompt else "🎤 [إدخال صوتي من الميكروفون]"
    
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            model_map = {"Gemini 3 Pro": "models/gemini-3-pro-preview", "Gemini 2.5 Flash": "models/gemini-2.5-flash"}
            model = genai.GenerativeModel(model_map.get(engine_choice, "models/gemini-2.5-flash"))
            
            # إرسال التعليمات مع مستوى التفكير
            full_prompt = f"بصفتك {persona} وبمستوى تفكير {thinking_level}: {user_txt}"
            
            content_parts = [full_prompt]
            if uploaded_file:
                if uploaded_file.type.startswith("image"):
                    content_parts.append(Image.open(uploaded_file))
                else:
                    content_parts.append(uploaded_file.read().decode())

            # إذا تم استخدام الميكروفون (المغرفون)
            if audio_record:
                # هنا يمكن إرسال الصوت مباشرة لموديلات Gemini 2.5 التي تدعم الصوت
                content_parts.append({"mime_type": "audio/wav", "data": audio_record['bytes']})

            response = model.generate_content(content_parts)
            st.markdown(response.text)
            
            # تحويل الرد لصوت مسموع (تكلم المنصة)
            tts = gTTS(text=response.text[:300], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3')
            
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e: st.error(f"خطأ: {e}")
