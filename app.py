import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder

# إعداد الصفحة
st.set_page_config(page_title="مصعب AI الشامل", page_icon="🎙️", layout="wide")

# تحميل مفتاح الـ API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("يرجى إضافة GEMINI_API_KEY في الإعدادات.")
    st.stop()

genai.configure(api_key=api_key)

# --- القائمة الجانبية ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    persona = st.selectbox("الشخصية:", ["مساعد عام", "خبير برمجيات", "مدرس لغات", "محلل بيانات"])
    model_choice = st.radio("المحرك:", ["gemini-2.5-flash", "gemma-3-27b-it", "توليد الصور (Imagen 3)"])
    
    st.divider()
    st.write("🎙️ إدخال صوتي:")
    audio_record = mic_recorder(
        start_prompt="إضغط للتحدث 🎤",
        stop_prompt="إرسال الصوت 📤",
        key='recorder'
    )
    
    st.divider()
    uploaded_file = st.file_uploader("ارفع صورة للتحليل:", type=["jpg", "jpeg", "png"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- دالة معالجة الردود ---
def get_ai_response(user_input, attached_image=None, attached_audio=None):
    model = genai.GenerativeModel(model_choice if model_choice != "توليد الصور (Imagen 3)" else "gemini-2.5-flash")
    content_list = [f"تقمص دور {persona}: {user_input}"]
    
    if attached_image:
        content_list.append(Image.open(attached_image))
    
    if attached_audio:
        # إرسال الصوت كبيانات بايتات للنموذج
        content_list.append({"mime_type": "audio/wav", "data": attached_audio})
    
    response = model.generate_content(content_list)
    return response.text

# --- واجهة التطبيق الرئيسية ---
if model_choice == "توليد الصور (Imagen 3)":
    st.header("🎨 صانع الصور")
    prompt = st.text_area("صف الصورة بالإنجليزية:")
    if st.button("إبدأ الرسم 🖌️"):
        if prompt:
            with st.spinner("جاري الرسم..."):
                try:
                    img_model = genai.GenerativeModel("imagen-3.0-generate-001")
                    result = img_model.generate_content(prompt)
                    st.image(result.candidates[0].content.parts[0].inline_data.data)
                except Exception as e: st.error(f"خطأ: {e}")
else:
    st.header(f"💬 الدردشة ({model_choice})")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # معالجة الإدخال (نصي أو صوتي)
    user_input = st.chat_input("اسألني أي شيء...")
    
    # إذا سجل المستخدم صوتاً، نعتبره هو المدخل
    current_audio = audio_record['bytes'] if audio_record else None
    
    if user_input or current_audio:
        input_text = user_input if user_input else "حلل هذا التسجيل الصوتي وأجب عليه."
        
        st.session_state.messages.append({"role": "user", "content": input_text})
        with st.chat_message("user"):
            st.markdown(input_text)
            if current_audio: st.audio(current_audio)

        with st.chat_message("assistant"):
            with st.spinner("جاري التفكير..."):
                try:
                    response_text = get_ai_response(input_text, uploaded_file, current_audio)
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception as e: st.error(f"حدث خطأ: {e}")
