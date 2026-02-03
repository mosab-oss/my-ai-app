import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import urllib.parse

# 1. إعدادات الصفحة
st.set_page_config(page_title="مساعد مصعب المتكامل", layout="wide", page_icon="⚡")

# إعداد مفتاح API (يتم جلبه من إعدادات Streamlit Secrets أو ملف .env)
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ مفتاح API غير موجود. يرجى إضافته في إعدادات التطبيق.")
    st.stop()

genai.configure(api_key=api_key)

# 2. دالة الرسم التلقائي (لضمان ظهور صور حقيقية)
def draw_image(description):
    encoded_desc = urllib.parse.quote(description)
    # استخدام محرك pollinations لضمان الحصول على رابط صورة مباشر
    return f"https://pollinations.ai/p/{encoded_desc}?width=1024&height=1024&seed=42"

# 3. واجهة التحكم الجانبية (Sidebar)
with st.sidebar:
    st.header("🎨 أدوات التحكم")
    # ميزة الميكروفون
    audio_record = mic_recorder(start_prompt="تحدث الآن 🎤", stop_prompt="إرسال 📤", key='recorder')
    st.divider()
    # ميزة رفع الصور
    uploaded_file = st.file_uploader("رفع صورة لتحليلها:", type=["jpg", "png", "jpeg"])
    if st.button("🗑️ مسح الذاكرة"):
        st.session_state.messages = []
        st.rerun()

# 4. الواجهة الرئيسية
st.title("⚡ مساعد مصعب المتكامل")
st.info("تم إصلاح خطأ NotFound وتفعيل محرك الرسم التلقائي.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض المحادثة السابقة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img_url" in msg: st.image(msg["img_url"])

# 5. معالجة الطلبات (نص، صوت، صورة)
user_input = st.chat_input("اطلب رسم صورة أو اسأل سؤالاً...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل المحتوى المرفق بدقة"
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner("جاري الاتصال بـ Gemini 3..."):
            # استخدام الاسم التقني الصحيح لتجنب خطأ NotFound
            model = genai.GenerativeModel("gemini-1.5-flash") # 1.5 هو الأكثر استقراراً حالياً لتجنب أخطاء المعاينة
            
            contents = [prompt]
            if uploaded_file: contents.append(Image.open(uploaded_file))
            if current_audio: contents.append({"mime_type": "audio/wav", "data": current_audio})
            
            try:
                response = model.generate_content(contents)
                answer = response.text
                
                # إظهار صورة إذا طلب المستخدم الرسم
                img_url = None
                if any(x in prompt for x in ["ارسم", "صورة", "تخيل", "draw", "image"]):
                    img_url = draw_image(prompt)
                    st.image(img_url, caption="الصورة الناتجة")

                st.markdown(answer)
                
                # الرد الصوتي التلقائي
                tts = gTTS(text=answer[:200], lang='ar')
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                st.audio(audio_fp, autoplay=True)
                
                # حفظ في الذاكرة
                new_msg = {"role": "assistant", "content": answer}
                if img_url: new_msg["img_url"] = img_url
                st.session_state.messages.append(new_msg)
                
            except Exception as e:
                st.error(f"⚠️ حدث خطأ أثناء التوليد: {e}")
