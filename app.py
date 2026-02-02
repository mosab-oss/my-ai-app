import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. إعدادات الصفحة والبيئة
st.set_page_config(page_title="مصعب AI - النسخة الكاملة", layout="wide", page_icon="⚡")
load_dotenv()

# 2. إعداد الاتصال بـ Google AI
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ لم يتم العثور على GEMINI_API_KEY في ملف .env")
    st.stop()

genai.configure(api_key=api_key)

# 3. دالة التوليد الذكية (Fallback Mechanism)
# هذه الدالة تضمن عدم توقف التطبيق إذا انتهت حصة Gemini 3
def smart_generate(contents):
    # ترتيب الموديلات: نبدأ بالأقوى ثم الأكثر توفراً
    models_to_try = ["gemini-3-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            return response.text, model_name
        except Exception as e:
            # إذا كان الخطأ بسبب الحصة (Quota 429)، انتقل للموديل التالي
            if "429" in str(e) or "quota" in str(e).lower():
                continue 
            else:
                return f"⚠️ خطأ تقني: {e}", None
    return "🚫 عذراً، انتهت جميع الحصص المجانية لجميع الموديلات اليوم.", None

# 4. دالة تحويل النص إلى صوت (النطق)
def speak(text):
    try:
        # تنظيف النص من الرموز ليكون النطق طبيعياً
        clean_text = text.replace('*', '').replace('#', '')
        tts = gTTS(text=clean_text[:300], lang='ar') # نطق أول 300 حرف لسرعة الاستجابة
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except:
        return None

# 5. واجهة القائمة الجانبية (الأدوات)
with st.sidebar:
    st.header("🎨 أدوات التحكم")
    
    # ميزة الميكروفون
    st.subheader("🎙️ تسجيل صوتي")
    audio_record = mic_recorder(
        start_prompt="إضغط للتحدث 🎤",
        stop_prompt="إرسال الصوت 📤",
        key='recorder'
    )
    
    st.divider()
    
    # ميزة الرؤية (Vision)
    st.subheader("🖼️ رفع صور")
    uploaded_file = st.file_uploader("اختر صورة لتحليلها:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح ذاكرة المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 6. الواجهة الرئيسية للمحادثة
st.title("⚡ مساعد مصعب المتكامل")
st.info("هذا التطبيق يتنقل تلقائياً بين الموديلات لضمان استمرار الخدمة.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل السابقة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال المدخلات (نصي، صوتي، أو صورة)
user_input = st.chat_input("اكتب رسالتك هنا...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    # تحديد النص الأساسي للطلب
    prompt = user_input if user_input else "حلل المرفقات"
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)
        if current_audio: st.audio(current_audio)

    with st.chat_message("assistant"):
        with st.spinner("جاري المعالجة..."):
            # تجهيز قائمة المحتويات لـ Gemini
            content_list = [prompt]
            if uploaded_file:
                content_list.append(Image.open(uploaded_file))
            if current_audio:
                # إرسال الصوت كمصفوفة بيانات
                content_list.append({"mime_type": "audio/wav", "data": current_audio})
            
            # تنفيذ التوليد الذكي
            response_text, model_used = smart_generate(content_list)
            
            if model_used:
                st.markdown(response_text)
                st.caption(f"🤖 تم الرد بواسطة: {model_used}")
                
                # تشغيل الرد الصوتي تلقائياً
                audio_fp = speak(response_text)
                if audio_fp:
                    st.audio(audio_fp, autoplay=True)
                
                # حفظ في الذاكرة
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            else:
                st.error(response_text)
