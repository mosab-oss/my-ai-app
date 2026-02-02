import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. إعداد الصفحة
st.set_page_config(page_title="مساعد مصعب الذكي", page_icon="🎙️", layout="wide")

# 2. تحميل مفتاح الـ API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("يرجى إضافة GEMINI_API_KEY في Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# 3. دالة تحويل النص إلى صوت
def speak_text(text):
    try:
        # تحويل النص لصوت (يدعم العربية والإنجليزية تلقائياً)
        tts = gTTS(text=text, lang='ar', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except Exception as e:
        st.error(f"خطأ في تحويل الصوت: {e}")
        return None

# 4. القائمة الجانبية
with st.sidebar:
    st.title("⚙️ الإعدادات")
    persona = st.selectbox("الشخصية:", ["مساعد عام", "خبير برمجيات", "مدرس لغات", "محلل بيانات"])
    model_choice = st.radio("المحرك:", ["gemini-2.5-flash", "gemma-3-27b-it", "توليد الصور (Imagen 3)"])
    
    st.divider()
    st.write("🎙️ تحدث مع التطبيق:")
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

# 5. منطق توليد الصور (Imagen 3)
if model_choice == "توليد الصور (Imagen 3)":
    st.header("🎨 صانع الصور الذكي")
    prompt = st.text_area("صف الصورة بالإنجليزية (لنتائج أفضل):")
    if st.button("إبدأ الرسم 🖌️"):
        if prompt:
            with st.spinner("جاري الرسم..."):
                try:
                    img_model = genai.GenerativeModel("imagen-3.0-generate-001")
                    result = img_model.generate_content(prompt)
                    st.image(result.candidates[0].content.parts[0].inline_data.data, caption="تصميم مصعب AI")
                except Exception as e:
                    st.error(f"خطأ في محرك الصور: {e}")
        else:
            st.warning("الرجاء كتابة وصف.")

# 6. منطق الدردشة والصوت (Gemini/Gemma)
else:
    st.header(f"💬 الدردشة الذكية ({model_choice})")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض الرسائل السابقة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # استقبال الإدخال
    user_input = st.chat_input("اكتب سؤالك هنا...")
    current_audio = audio_record['bytes'] if audio_record else None
    
    if user_input or current_audio:
        # تحديد النص المرسل
        final_text = user_input if user_input else "حلل هذا التسجيل الصوتي وأجب عليه."
        
        # عرض رسالة المستخدم
        st.session_state.messages.append({"role": "user", "content": final_text})
        with st.chat_message("user"):
            st.markdown(final_text)
            if current_audio:
                st.audio(current_audio)

        # توليد رد الذكاء الاصطناعي
        with st.chat_message("assistant"):
            with st.spinner("جاري التفكير والنطق..."):
                try:
                    model = genai.GenerativeModel(model_choice)
                    content_list = [f"تقمص دور {persona}: {final_text}"]
                    
                    if uploaded_file:
                        content_list.append(Image.open(uploaded_file))
                    if current_audio:
                        content_list.append({"mime_type": "audio/wav", "data": current_audio})
                    
                    # الحصول على الرد النصي
                    response = model.generate_content(content_list)
                    response_text = response.text
                    
                    # عرض النص
                    st.markdown(response_text)
                    
                    # توليد وتشغيل الصوت
                    audio_fp = speak_text(response_text)
                    if audio_fp:
                        st.audio(audio_fp, format='audio/mp3', autoplay=True)
                    
                    # حفظ في السجل
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    
                except Exception as e:
                    st.error(f"حدث خطأ: {e}")
