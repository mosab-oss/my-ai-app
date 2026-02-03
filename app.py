import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import re

# 1. إعدادات الصفحة والواجهة
st.set_page_config(page_title="مساعد مصعب المتكامل", layout="wide", page_icon="⚡")

# إعداد مفتاح API (تأكد من وجوده في Secrets)
api_key = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 2. دالة التوليد الذكية (Gemini 3 Flash Preview كما في صورتك)
def smart_generate(contents):
    model_name = "gemini-3-flash-preview"
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(contents)
        return response.text, model_name
    except Exception as e:
        return f"⚠️ خطأ: {e}", None

# 3. دالة معالجة الرد (لإخفاء الـ Thought وإظهار الصور)
def process_response(text):
    # استخراج رابط الصورة إذا وجد
    img_urls = re.findall(r'(https?://\S+?\.(?:png|jpg|jpeg|gif))', text)
    
    # تنظيف النص من أفكار الموديل (Thought) وأكواد JSON المزعجة
    clean_text = re.sub(r'\{.*?\}', '', text, flags=re.DOTALL)
    clean_text = re.sub(r'"thought":.*?,', '', clean_text, flags=re.DOTALL)
    clean_text = clean_text.replace('"', '').replace('thought:', '').strip()
    
    return clean_text if clean_text else "تمت المعالجة بنجاح.", img_urls

# 4. واجهة التحكم الجانبية (إعادة الميزات المفقودة)
with st.sidebar:
    st.header("🎨 أدوات التحكم")
    st.subheader("🎙️ التسجيل الصوتي")
    audio_record = mic_recorder(start_prompt="تحدث الآن 🎤", stop_prompt="إرسال 📤", key='recorder')
    
    st.divider()
    st.subheader("🖼️ رفع الصور")
    uploaded_file = st.file_uploader("اختر صورة لتحليلها:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح الذاكرة"):
        st.session_state.messages = []
        st.rerun()

# 5. الواجهة الرئيسية
st.title("⚡ مساعد مصعب المتكامل")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 6. معالجة المدخلات (نص، صوت، صورة)
user_input = st.chat_input("اطلب رسم صورة أو اسأل سؤالاً...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل المرفقات بدقة"
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner("جاري التوليد بواسطة Gemini 3..."):
            contents = [prompt]
            if uploaded_file: contents.append(Image.open(uploaded_file))
            if current_audio: contents.append({"mime_type": "audio/wav", "data": current_audio})
            
            raw_text, m_used = smart_generate(contents)
            
            if m_used:
                clean_text, images = process_response(raw_text)
                
                # عرض الصور المولدة إن وجدت
                if images:
                    for img_url in images:
                        st.image(img_url, caption="الصورة المولدة")
                
                # عرض النص النظيف
                st.markdown(clean_text)
                st.caption(f"🤖 المحرك: {m_used}")
                
                # إعادة ميزة الرد الصوتي تلقائياً
                try:
                    tts = gTTS(text=clean_text[:250], lang='ar')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, autoplay=True)
                except: pass
                
                st.session_state.messages.append({"role": "assistant", "content": clean_text})
