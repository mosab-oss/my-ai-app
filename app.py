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

# الربط المحلي (LM Studio) ومحركات جوجل
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية الشاملة ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.11.9")
    
    st.subheader("🎤 المغرفون (للتكلم)")
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
        ["المعرفون (أهل العلم)", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"]
    )
    
    st.divider()
    
    engine_choice = st.selectbox(
        "🎯 المحرك:",
        ["DeepSeek R1 (Local)", "Gemini 2.5 Flash", "Gemini 3 Pro"]
    )
    
    uploaded_file = st.file_uploader("📂 رفع الملفات:", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    st.divider()
    
    if st.button("🔍 فحص الموديلات النشطة"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.info("الموديلات المتاحة:")
            st.code("\n".join(models))
        except Exception as e: st.error(f"خطأ: {e}")

# --- 3. واجهة الدردشة الرئيسية ---
if "messages" not in st.session_state: 
    st.session_state.messages = []

# عرض تاريخ الدردشة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): 
        st.markdown(msg["content"])

# --- كود طلب الرد المدمج (المعدل بناءً على صورتك) ---
if prompt := st.chat_input("اسأل ذكاءك الاصطناعي المحلي..."):
    # إضافة رسالة المستخدم للتاريخ والعرض
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # طلب الرد من المحرك المحلي
    with st.chat_message("assistant"):
        try:
            stream = local_client.chat.completions.create(
                # تم تعديل الاسم هنا بناءً على الـ Identifier في صورتك
                model="deepseek-r1-distill-qwen-1.5b",
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            # عرض الرد أثناء تدفقه (Streaming)
            answer = st.write_stream(stream)
            
            # حفظ رد المساعد في التاريخ
            st.session_state.messages.append({"role": "assistant", "content": answer})
            
        except Exception as e:
            st.error(f"تأكد من تشغيل الخادم وتحميل الموديل في LM Studio. الخطأ: {e}")
