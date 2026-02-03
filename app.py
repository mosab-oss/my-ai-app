import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. إعدادات الصفحة والبيئة
st.set_page_config(page_title="مساعد مصعب المتكامل", layout="wide", page_icon="⚡")
load_dotenv()

# 2. إعداد الاتصال بمفتاح الـ API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ لم يتم العثور على المفتاح. تأكد من إضافته في Secrets أو ملف .env")
    st.stop()

genai.configure(api_key=api_key)

# 3. دالة التوليد الذكية (تحديث الأسماء التقنية)
def smart_generate(contents):
    # القائمة المحدثة بناءً على صور حسابك في AI Studio
    models_to_try = [
        "gemini-3-flash-preview",  # المحرك الرئيسي الذي ظهر في صورتك
        "gemini-2.0-flash-exp",    # المحرك البديل القوي
        "gemini-1.5-flash",        # المحرك الاحتياطي المستقر
    ]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            return response.text, model_name
        except Exception as e:
            # تخطي أخطاء الـ 404 (غير موجود) والـ 429 (انتهت الحصة)
            if "404" in str(e) or "429" in str(e) or "quota" in str(e).lower():
                continue 
            else:
                return f"⚠️ خطأ تقني غير متوقع: {e}", None
    return "🚫 عذراً، جميع المحركات غير متاحة حالياً. جرب لاحقاً.", None

# 4. دالة النطق الصوتي (الرد الصوتي)
def speak(text):
    try:
        # تنظيف النص من الرموز لضمان نطق سليم
        clean_text = text.replace('*', '').replace('#', '')
        tts = gTTS(text=clean_text[:300], lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except:
        return None

# 5. واجهة الأدوات الجانبية (صوت وصورة)
with st.sidebar:
    st.header("🎨 أدوات التحكم")
    
    # ميزة الميكروفون
    st.subheader("🎙️ الميكروفون")
    audio_record = mic_recorder(
        start_prompt="إبدأ التحدث 🎤",
        stop_prompt="إرسال الصوت 📤",
        key='recorder'
    )
    
    st.divider()
    
    # ميزة الرؤية (تحميل الصور)
    st.subheader("🖼️ تحليل الصور")
    uploaded_file = st.file_uploader("ارفع صورة لنحللها:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح ذاكرة المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 6. الواجهة الرئيسية
st.title("⚡ مساعد مصعب الذكي")
st.write("هذا التطبيق مجهز بـ Gemini 3 وميزة التنقل التلقائي لتجاوز القيود.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض المحادثة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال المدخلات (نص، صوت، صورة)
user_input = st.chat_input("اكتب سؤالك هنا...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل المحتوى المرفق"
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner("جاري اختيار أفضل محرك متاح والرد عليك..."):
            # تجهيز قائمة المحتويات
            content_list = [prompt]
            if uploaded_file:
                content_list.append(Image.open(uploaded_file))
            if current_audio:
                content_list.append({"mime_type": "audio/wav", "data": current_audio})
            
            # تنفيذ التوليد مع ميزة Fallback
            answer, used_model = smart_generate(content_list)
            
            if used_model:
                st.markdown(answer)
                st.caption(f"🤖 تم استخدام المحرك: {used_model}")
                
                # نطق الإجابة تلقائياً
                audio_fp = speak(answer)
                if audio_fp:
                    st.audio(audio_fp, autoplay=True)
                
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                st.error(answer)
