import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import re
import urllib.parse

# 1. إعدادات الصفحة
st.set_page_config(page_title="مساعد مصعب المتكامل", layout="wide", page_icon="⚡")

# إعداد مفتاح API
api_key = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 2. دالة الرسم التلقائي (لحل مشكلة عدم ظهور الصور)
def get_image_url(description):
    # تحويل الوصف النصي إلى رابط صورة حقيقي من محرك رسم مجاني
    encoded_desc = urllib.parse.quote(description)
    return f"https://pollinations.ai/p/{encoded_desc}?width=1024&height=1024&seed=42"

# 3. واجهة التحكم الجانبية
with st.sidebar:
    st.header("🎨 أدوات التحكم")
    audio_record = mic_recorder(start_prompt="تحدث الآن 🎤", stop_prompt="إرسال 📤", key='recorder')
    st.divider()
    uploaded_file = st.file_uploader("رفع صورة لتحليلها:", type=["jpg", "png", "jpeg"])
    if st.button("🗑️ مسح الذاكرة"):
        st.session_state.messages = []
        st.rerun()

# 4. الواجهة الرئيسية
st.title("⚡ مساعد مصعب المتكامل")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img_url" in msg: st.image(msg["img_url"])

# 5. معالجة الطلبات
user_input = st.chat_input("اطلب رسم صورة أو اسأل سؤالاً...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل المرفق بدقة"
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner("جاري المعالجة..."):
            model = genai.GenerativeModel("gemini-1.5-flash") # نستخدم 1.5 لاستقرار أفضل في إرسال الردود
            contents = [prompt]
            if uploaded_file: contents.append(Image.open(uploaded_file))
            if current_audio: contents.append({"mime_type": "audio/wav", "data": current_audio})
            
            response = model.generate_content(contents)
            answer = response.text
            
            # تنظيف الرد من أفكار الموديل المزعجة
            answer = re.sub(r'\{.*?\}', '', answer, flags=re.DOTALL).strip()
            
            # هل طلب المستخدم صورة؟
            img_url = None
            if any(word in prompt for word in ["ارسم", "صورة", "تخيل", "draw", "image"]):
                img_url = get_image_url(prompt)
                st.image(img_url, caption="الصورة التي رسمتها لك")

            st.markdown(answer)
            
            # الرد الصوتي
            try:
                tts = gTTS(text=answer[:200], lang='ar')
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                st.audio(audio_fp, autoplay=True)
            except: pass
            
            new_msg = {"role": "assistant", "content": answer}
            if img_url: new_msg["img_url"] = img_url
            st.session_state.messages.append(new_msg)
