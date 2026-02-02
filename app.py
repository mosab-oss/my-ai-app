import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. إعدادات الصفحة والواجهة
st.set_page_config(page_title="مصعب AI - المساعد الشامل", page_icon="🚀", layout="wide")

# 2. إعدادات مفتاح الـ API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("خطأ: يرجى إضافة مفتاح GEMINI_API_KEY في إعدادات التطبيق (Secrets).")
    st.stop()

genai.configure(api_key=api_key)

# 3. وظيفة تحويل النص إلى رد صوتي مسموع
def speak_text(text):
    try:
        # تنظيف النص من الرموز البرمجية لجعل النطق طبيعياً
        clean_text = text.replace('*', '').replace('#', '').replace('_', '')
        tts = gTTS(text=clean_text, lang='ar', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except:
        return None

# 4. القائمة الجانبية (الإعدادات والوسائط المرفوعة)
with st.sidebar:
    st.title("⚙️ لوحة التحكم")
    persona = st.selectbox("شخصية الذكاء الاصطناعي:", ["مساعد عام", "خبير برمجيات", "مدرس لغات", "محلل تقني"])
    model_choice = st.radio("اختر المحرك:", ["gemini-2.5-flash", "gemma-3-27b-it", "توليد الصور (Imagen)"])
    
    st.divider()
    st.subheader("🖼️ الرؤية والتحليل (Vision)")
    # الجزء الذي طلبته: رفع الصور للتحليل
    uploaded_file = st.file_uploader("ارفع صورة لنناقشها:", type=["jpg", "jpeg", "png"])
    
    st.divider()
    st.subheader("🎙️ الأوامر الصوتية")
    audio_record = mic_recorder(start_prompt="تحدث الآن 🎤", stop_prompt="إرسال ومعالجة 📤", key='recorder')
    
    if st.button("🗑️ مسح سجل المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 5. منطق توليد الصور (Imagen)
if model_choice == "توليد الصور (Imagen)":
    st.header("🎨 محرك الرسم الذكي")
    prompt = st.text_area("صف الصورة التي تريد رسمها بالإنجليزية:")
    if st.button("إبدأ الرسم 🖌️"):
        if prompt:
            with st.spinner("جاري الرسم..."):
                try:
                    model = genai.GenerativeModel('imagen-3.0-generate-001')
                    result = model.generate_content(prompt)
                    st.image(result.candidates[0].content.parts[0].inline_data.data, caption="تصميم مصعب AI")
                except Exception as e:
                    st.error(f"خطأ في محرك الرسم: {e}")
        else:
            st.warning("يرجى كتابة وصف.")

# 6. منطق الدردشة الشامل (نص + صورة + صوت)
else:
    st.header(f"💬 الدردشة والتحليل الذكي ({model_choice})")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض الرسائل القديمة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # استقبال المدخلات (سواء كانت نصية، صوتية، أو صوراً)
    user_input = st.chat_input("اكتب سؤالك هنا أو ارفع صورة لنحللها...")
    current_audio = audio_record['bytes'] if audio_record else None
    
    if user_input or current_audio or uploaded_file:
        # تحديد طبيعة السؤال بناءً على المدخلات
        if user_input:
            final_query = user_input
        elif current_audio:
            final_query = "حلل هذا التسجيل الصوتي وأجب عليه بناءً على أي صورة مرفقة إن وجدت."
        else:
            final_query = "اشرح لي ماذا ترى في هذه الصورة بالتفصيل."

        # عرض رسالة المستخدم
        st.session_state.messages.append({"role": "user", "content": final_query})
        with st.chat_message("user"):
            st.markdown(final_query)
            if uploaded_file:
                st.image(uploaded_file, width=300, caption="الصورة المراد تحليلها")
            if current_audio:
                st.audio(current_audio)

        # توليد رد الذكاء الاصطناعي (تحليل شامل)
        with st.chat_message("assistant"):
            with st.spinner("جاري التحليل وتوليد الرد الصوتي..."):
                try:
                    model = genai.GenerativeModel(model_choice)
                    
                    # دمج كل الحواس في قائمة واحدة للمحرك
                    content_list = [f"تقمص دور {persona}: {final_query}"]
                    
                    if uploaded_file:
                        content_list.append(Image.open(uploaded_file)) # الرؤية
                    
                    if current_audio:
                        content_list.append({"mime_type": "audio/wav", "data": current_audio}) # الصوت
                    
                    # الحصول على الرد
                    response = model.generate_content(content_list)
                    response_text = response.text
                    
                    # عرض الرد نصياً
                    st.markdown(response_text)
                    
                    # تحويل الرد إلى صوت وتشغيله تلقائياً
                    audio_output = speak_text(response_text)
                    if audio_output:
                        st.audio(audio_output, format='audio/mp3', autoplay=True)
                    
                    # حفظ الرد في السجل
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"حدث خطأ أثناء المعالجة: {e}")
