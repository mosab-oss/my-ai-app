import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. إعدادات الصفحة
st.set_page_config(page_title="مصعب AI - جيل Gemini 3", page_icon="⚡", layout="wide")

# 2. إعداد الـ API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("يرجى إضافة مفتاح الـ API في الإعدادات.")
    st.stop()

genai.configure(api_key=api_key)

# 3. دالة الصوت
def speak_text(text):
    try:
        tts = gTTS(text=text.replace('*', ''), lang='ar', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

# 4. القائمة الجانبية (الرؤية + المحرك الجديد)
with st.sidebar:
    st.title("🚀 لوحة تحكم Gemini 3")
    # تحديث الموديل ليطابق شاشتك (Gemini 3 Flash)
    model_choice = st.radio("المحرك النشط:", ["gemini-3-flash-preview", "🎨 رسم بالذكاء (Imagen 4)"])
    
    st.divider()
    st.subheader("🖼️ الرؤية والتحليل (Vision)")
    uploaded_file = st.file_uploader("ارفع صورة لتحليلها:", type=["jpg", "jpeg", "png"])
    
    st.divider()
    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')

# 5. منطق توليد الصور (Imagen 4)
if "رسم" in model_choice:
    st.header("🎨 محرك Imagen 4 الجديد")
    prompt = st.text_area("صف الصورة بالإنجليزية:")
    if st.button("توليد الصورة 🖌️"):
        with st.spinner("جاري الرسم باستخدام Imagen 4..."):
            try:
                # تحديث اسم الموديل ليطابق المتاح في حسابك
                model = genai.ImageGenerationModel("imagen-4")
                result = model.generate_images(prompt=prompt, number_of_images=1)
                st.image(result.images[0]._pil_image)
            except Exception as e:
                st.error(f"تأكد من تفعيل VPN أمريكي، الخطأ: {e}")

# 6. منطق الدردشة والرؤية (Gemini 3 Flash)
else:
    st.header("💬 مساعد مصعب (Gemini 3 Flash)")
    if "messages" not in st.session_state: st.session_state.messages = []

    user_input = st.chat_input("اسأل عن الصورة أو دردش...")
    current_audio = audio_record['bytes'] if audio_record else None

    if user_input or current_audio or uploaded_file:
        query = user_input if user_input else "حلل المحتوى المرفق."
        
        with st.chat_message("user"):
            st.markdown(query)
            if uploaded_file: st.image(uploaded_file, width=300)

        with st.chat_message("assistant"):
            try:
                # استخدام Gemini 3 Flash كما يظهر في شاشتك
                model = genai.GenerativeModel("gemini-3-flash-preview")
                content = [f"بصفتك مساعد مصعب: {query}"]
                if uploaded_file: content.append(Image.open(uploaded_file))
                
                response = model.generate_content(content)
                st.markdown(response.text)
                
                # الرد الصوتي التلقائي
                audio_output = speak_text(response.text)
                if audio_output: st.audio(audio_output, format='audio/mp3', autoplay=True)
            except Exception as e: st.error(f"خطأ: {e}")
