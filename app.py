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

# 2. إعداد الـ API (تأكد من وجود المفتاح في ملف .env أو Secrets)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("يرجى إضافة مفتاح الـ API الخاص بك.")
    st.stop()

genai.configure(api_key=api_key)

# 3. دالة تحويل النص إلى صوت
def speak_text(text):
    try:
        clean_text = text.replace('*', '').replace('#', '')
        tts = gTTS(text=clean_text, lang='ar', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

# 4. القائمة الجانبية (Sidebar) - تحتوي على زر الحذف والرؤية
with st.sidebar:
    st.title("🚀 لوحة تحكم Gemini 3")
    persona = st.selectbox("شخصية المساعد:", ["مساعد عام", "خبير برمجيات", "مدرس لغات"])
    
    # اختيار الموديل كما يظهر في حسابك
    model_choice = st.radio("المحرك النشط:", ["gemini-3-flash-preview", "🎨 رسم بالذكاء (Imagen 4)"])
    
    st.divider()
    
    # --- ميزة الرؤية والتحليل (Vision) ---
    st.subheader("🖼️ الرؤية والتحليل")
    uploaded_file = st.file_uploader("ارفع صورة (كود، نص، منظر):", type=["jpg", "jpeg", "png"])
    
    st.divider()
    
    # --- الأوامر الصوتية ---
    st.subheader("🎙️ الأوامر الصوتية")
    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')
    
    st.divider()
    
    # --- زر مسح المحادثة (الذي كنت تبحث عنه) ---
    if st.button("🗑️ مسح سجل المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 5. منطق الدردشة والرؤية الشامل
st.header(f"💬 مساعد مصعب الذكي (Gemini 3 Flash)")

if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل القديمة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال المدخلات
user_input = st.chat_input("دردش هنا أو اسأل عن الصورة...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    # صياغة الاستعلام
    if user_input:
        query = user_input
    elif current_audio:
        query = "حلل الصوت المرفق وأجب عليه."
    else:
        query = "اشرح لي ماذا يوجد في هذه الصورة."

    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
        if uploaded_file: st.image(uploaded_file, width=300)

    # توليد الرد من Gemini 3
    with st.chat_message("assistant"):
        with st.spinner("جاري التحليل والنطق..."):
            try:
                model = genai.GenerativeModel("gemini-3-flash-preview")
                content_list = [f"بصفتك {persona}: {query}"]
                
                # إضافة الصورة للتحليل (Vision)
                if uploaded_file:
                    content_list.append(Image.open(uploaded_file))
                
                # إضافة الصوت للتحليل
                if current_audio:
                    content_list.append({"mime_type": "audio/wav", "data": current_audio})
                
                response = model.generate_content(content_list)
                st.markdown(response.text)
                
                # الرد الصوتي
                audio_fp = speak_text(response.text)
                if audio_fp:
                    st.audio(audio_fp, format='audio/mp3', autoplay=True)
                
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
