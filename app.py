import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="مصعب AI المتكامل", page_icon="🚀", layout="wide")

# 2. إعداد المفاتيح
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("يرجى إضافة GEMINI_API_KEY في إعدادات Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# 3. دالة الصوت (تحويل الرد لصوت مسموع)
def speak_text(text):
    try:
        clean_text = text.replace('*', '').replace('#', '')
        tts = gTTS(text=clean_text, lang='ar', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

# 4. القائمة الجانبية (الإعدادات + الرؤية + الصوت)
with st.sidebar:
    st.title("⚙️ الإعدادات والوسائط")
    persona = st.selectbox("شخصية المساعد:", ["مساعد عام", "خبير برمجيات", "مدرس لغات"])
    model_choice = st.radio("المحرك:", ["gemini-2.5-flash", "gemma-3-27b-it", "توليد الصور (Imagen)"])
    
    st.divider()
    st.subheader("🖼️ الرؤية والتحليل (Vision)")
    # رفع الصور لتحليلها (أكواد، نصوص، مناظر)
    uploaded_file = st.file_uploader("ارفع صورة لنناقشها:", type=["jpg", "jpeg", "png"])
    
    st.divider()
    st.subheader("🎙️ الأوامر الصوتية")
    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 5. منطق توليد الصور (Imagen)
if model_choice == "توليد الصور (Imagen)":
    st.header("🎨 محرك الرسم الذكي")
    prompt = st.text_area("صف الصورة بالإنجليزية:")
    if st.button("إبدأ الرسم 🖌️"):
        if prompt:
            with st.spinner("جاري الرسم..."):
                try:
                    # الطريقة المستقرة لاستدعاء Imagen
                    imagen_model = genai.ImageGenerationModel("imagen-3.0-generate-001")
                    result = imagen_model.generate_images(prompt=prompt, number_of_images=1)
                    st.image(result.images[0]._pil_image, caption="تصميم مصعب AI")
                except Exception as e:
                    st.error(f"خطأ في محرك الرسم: {e}")
        else: st.warning("يرجى كتابة وصف.")

# 6. منطق الدردشة الشامل (الرؤية + الصوت + النص)
else:
    st.header(f"💬 الدردشة والتحليل ({model_choice})")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    user_input = st.chat_input("دردش هنا أو اسأل عن الصورة...")
    current_audio = audio_record['bytes'] if audio_record else None
    
    if user_input or current_audio or uploaded_file:
        # تحديد نص السؤال
        if user_input:
            query = user_input
        elif current_audio:
            query = "حلل هذا التسجيل الصوتي وأجب عليه بناءً على الوسائط."
        else:
            query = "حلل هذه الصورة بالتفصيل."

        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
            if uploaded_file: st.image(uploaded_file, width=300, caption="الصورة المراد تحليلها")
            if current_audio: st.audio(current_audio)

        with st.chat_message("assistant"):
            with st.spinner("جاري التحليل والنطق..."):
                try:
                    model = genai.GenerativeModel(model_choice)
                    content_list = [f"تقمص دور {persona}: {query}"]
                    
                    if uploaded_file:
                        content_list.append(Image.open(uploaded_file)) # تفعيل الرؤية
                    
                    if current_audio:
                        content_list.append({"mime_type": "audio/wav", "data": current_audio}) # تفعيل الصوت
                    
                    response = model.generate_content(content_list)
                    response_text = response.text
                    
                    st.markdown(response_text)
                    
                    # الرد الصوتي التلقائي
                    audio_fp = speak_text(response_text)
                    if audio_fp:
                        st.audio(audio_fp, format='audio/mp3', autoplay=True)
                    
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception as e: st.error(f"حدث خطأ: {e}")
