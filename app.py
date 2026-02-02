import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder  # استدعاء الميكروفون
from gtts import gTTS
import io

# 1. الإعدادات الأساسية
st.set_page_config(page_title="مصعب AI - النسخة الكاملة", layout="wide")
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("يرجى إضافة GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=api_key)

# 2. وظيفة الصوت (الرد الصوتي)
def speak(text):
    try:
        clean_text = text.replace('*', '').replace('#', '')
        tts = gTTS(text=clean_text, lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

# 3. وظيفة الرسم الذكي
def draw_smart_image(user_prompt):
    try:
        # تحسين الوصف أولاً
        desc_model = genai.GenerativeModel("gemini-3-flash-preview")
        enhanced_prompt = desc_model.generate_content(f"Enhance this for Imagen 3: {user_prompt}").text
        # الرسم
        paint_model = genai.GenerativeModel("imagen-3.0-generate-001")
        response = paint_model.generate_content(enhanced_prompt)
        return response.candidates[0].content.parts[0].inline_data.data
    except Exception as e: return f"error: {e}"

# 4. القائمة الجانبية (هنا تظهر النوافذ المفقودة)
with st.sidebar:
    st.header("⚙️ التحكم والوسائط")
    mode = st.radio("اختر الوضع:", ["دردشة ورؤية 💬", "رسم احترافي 🎨"])
    
    st.divider()
    
    # نافذة الميكروفون (المغريفون)
    st.subheader("🎙️ تسجيل صوتي")
    audio_record = mic_recorder(
        start_prompt="بدء التسجيل 🎤",
        stop_prompt="إرسال الصوت 📤",
        key='recorder'
    )
    
    st.divider()
    
    # نافذة الرؤية (Vision)
    st.subheader("🖼️ تحليل الصور")
    uploaded_file = st.file_uploader("ارفع صورة:", type=["jpg", "png"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 5. منطقة العمل الرئيسية
st.title("⚡ مساعد مصعب الذكي")

if mode == "رسم احترافي 🎨":
    prompt = st.text_input("ماذا تريدني أن أرسم؟")
    if st.button("توليد اللوحة"):
        with st.spinner("جاري الرسم..."):
            result = draw_smart_image(prompt)
            if isinstance(result, str) and "error" in result:
                st.error("فشل الرسم. تأكد من VPN أمريكي.")
            else: st.image(result)

else:
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    user_input = st.chat_input("اكتب رسالتك هنا...")
    
    # التقاط المدخلات الصوتية
    current_audio = audio_record['bytes'] if audio_record else None

    if user_input or current_audio or uploaded_file:
        query = user_input if user_input else ("حلل الصوت المرفق" if current_audio else "حلل الصورة")
        
        with st.chat_message("user"):
            st.markdown(query)
            if uploaded_file: st.image(uploaded_file, width=300)
            if current_audio: st.audio(current_audio)

        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel("gemini-3-flash-preview")
                content = [query]
                if uploaded_file: content.append(Image.open(uploaded_file))
                if current_audio: content.append({"mime_type": "audio/wav", "data": current_audio})
                
                response = model.generate_content(content)
                st.markdown(response.text)
                
                # الرد الصوتي
                audio_fp = speak(response.text)
                if audio_fp: st.audio(audio_fp, autoplay=True)
                
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e: st.error(f"خطأ: {e}")
