import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io

# 1. إعدادات الصفحة الأساسية
st.set_page_config(page_title="مصعب AI - المساعد المتكامل", page_icon="🚀", layout="wide")

# 2. إعدادات المفاتيح والاتصال
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("يرجى إضافة مفتاح GEMINI_API_KEY في إعدادات التطبيق.")
    st.stop()

genai.configure(api_key=api_key)

# 3. وظيفة تحويل النص إلى كلام (Audio Output)
def speak_text(text):
    try:
        clean_text = text.replace('*', '').replace('#', '') # تنظيف النص من علامات التنسيق لقراءة أوضح
        tts = gTTS(text=clean_text, lang='ar', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except:
        return None

# 4. القائمة الجانبية (الأدوات والإعدادات)
with st.sidebar:
    st.header("⚙️ الإعدادات والوسائط")
    persona = st.selectbox("شخصية الذكاء الاصطناعي:", ["مساعد عام", "خبير برمجيات", "مدرس لغات", "محلل تقني"])
    model_choice = st.radio("اختر المحرك:", ["gemini-2.5-flash", "gemma-3-27b-it", "توليد الصور (Imagen 3)"])
    
    st.divider()
    st.subheader("🖼️ تحليل الصور (Vision)")
    uploaded_file = st.file_uploader("ارفع صورة لنناقشها:", type=["jpg", "jpeg", "png"])
    
    st.divider()
    st.subheader("🎙️ الأوامر الصوتية")
    audio_record = mic_recorder(start_prompt="تحدث الآن 🎤", stop_prompt="إرسال ومعالجة 📤", key='recorder')
    
    if st.button("🗑️ مسح ذاكرة المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 5. وضع توليد الصور (Imagen)
if model_choice == "توليد الصور (Imagen 3)":
    st.header("🎨 محرك الرسم الذكي")
    prompt = st.text_area("صف الصورة التي تتخيلها (بالإنجليزية لنتائج أفضل):")
    if st.button("إبدأ عملية الرسم 🖌️"):
        if prompt:
            with st.spinner("جاري الرسم..."):
                try:
                    imagen = genai.ImageGenerationModel("imagen-3.0-generate-001")
                    result = imagen.generate_images(prompt=prompt, number_of_images=1)
                    st.image(result.images[0]._pil_image, caption="تم التوليد بواسطة مصعب AI")
                except Exception as e:
                    st.error(f"عذراً، حدث خطأ في محرك الصور: {e}")
        else:
            st.warning("يرجى كتابة وصف للصورة.")

# 6. وضع الدردشة المتعددة (نص + صورة + صوت)
else:
    st.header(f"💬 مساعدك الذكي ({model_choice})")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض الرسائل السابقة
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # معالجة المدخلات
    user_input = st.chat_input("اكتب سؤالك هنا أو استخدم الميكروفون...")
    current_audio_bytes = audio_record['bytes'] if audio_record else None
    
    # التحقق من وجود أي نوع من المدخلات
    if user_input or current_audio_bytes or uploaded_file:
        # تحديد النص الأساسي للطلب
        if user_input:
            final_query = user_input
        elif current_audio_bytes:
            final_query = "حلل هذا التسجيل الصوتي وأجب عليه بناءً على أي وسائط مرفقة."
        else:
            final_query = "اشرح لي ما تراه في هذه الصورة بالتفصيل."

        # إضافة رسالة المستخدم للواجهة
        st.session_state.messages.append({"role": "user", "content": final_query})
        with st.chat_message("user"):
            st.markdown(final_query)
            if uploaded_file: st.image(uploaded_file, width=300, caption="الصورة المرفوعة")
            if current_audio_bytes: st.audio(current_audio_bytes)

        # توليد الرد من الذكاء الاصطناعي
        with st.chat_message("assistant"):
            with st.spinner("جاري التحليل وتوليد الرد الصوتي..."):
                try:
                    model = genai.GenerativeModel(model_choice)
                    
                    # بناء قائمة المحتوى المتعدد (Multimodal List)
                    content_to_send = [f"بصفتك {persona}: {final_query}"]
                    
                    if uploaded_file:
                        content_to_send.append(Image.open(uploaded_file))
                    
                    if current_audio_bytes:
                        content_to_send.append({"mime_type": "audio/wav", "data": current_audio_bytes})
                    
                    # طلب الرد
                    response = model.generate_content(content_to_send)
                    response_text = response.text
                    
                    # عرض النص
                    st.markdown(response_text)
                    
                    # توليد الصوت للرد
                    audio_output = speak_text(response_text)
                    if audio_output:
                        st.audio(audio_output, format='audio/mp3', autoplay=True)
                    
                    # حفظ في السجل
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"خطأ في المعالجة: {e}")
