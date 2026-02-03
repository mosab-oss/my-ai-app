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

# 3. دالة التوليد الذكية (تحديث الأسماء التقنية لتجاوز خطأ 404)
def smart_generate(contents):
    # هذه القائمة تستخدم الأسماء الدقيقة التي تقبلها جوجل حالياً في إصدار v1beta
    models_to_try = [
        "gemini-3-flash-preview",  # الاسم الصحيح لـ Gemini 3 كما في صورتك
        "gemini-2.0-flash-exp",    # النسخة التجريبية القوية 2.0
        "gemini-1.5-flash",        # النسخة المستقرة كاحتياط
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
                return f"⚠️ خطأ تقني: {e}", None
    return "🚫 عذراً، جميع المحركات غير متاحة حالياً. جرب لاحقاً.", None

# 4. دالة النطق الصوتي
def speak(text):
    try:
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
    st.subheader("🎙️ الميكروفون")
    audio_record = mic_recorder(start_prompt="إبدأ التحدث 🎤", stop_prompt="إرسال الصوت 📤", key='recorder')
    
    st.divider()
    st.subheader("🖼️ تحليل الصور")
    uploaded_file = st.file_uploader("ارفع صورة لنحللها:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح ذاكرة المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 6. الواجهة الرئيسية
st.title("⚡ مساعد مصعب الذكي")
st.info("تم تحديث أسماء الموديلات لتجنب خطأ 404 وتفعيل Gemini 3 Preview.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال المدخلات
user_input = st.chat_input("اكتب سؤالك هنا...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل المحتوى المرفق"
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner("جاري اختيار أفضل محرك متاح..."):
            content_list = [prompt]
            if uploaded_file:
                content_list.append(Image.open(uploaded_file))
            if current_audio:
                content_list.append({"mime_type": "audio/wav", "data": current_audio})
            
            answer, used_model = smart_generate(content_list)
            
            if used_model:
                st.markdown(answer)
                st.caption(f"🤖 تم الرد بواسطة: {used_model}")
                
                audio_fp = speak(answer)
                if audio_fp:
                    st.audio(audio_fp, autoplay=True)
                
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                st.error(answer)
