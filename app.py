import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import re
import urllib.parse

# 1. إعدادات الصفحة والاتصال
st.set_page_config(page_title="مساعد مصعب المتكامل", layout="wide", page_icon="⚡")

# جلب المفتاح بشكل آمن
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ يرجى إضافة GEMINI_API_KEY في إعدادات Streamlit.")
    st.stop()

genai.configure(api_key=api_key)

# 2. دالة الرسم التلقائي (لحل مشكلة عدم ظهور الصور)
def draw_image(description):
    encoded_desc = urllib.parse.quote(description)
    return f"https://pollinations.ai/p/{encoded_desc}?width=1024&height=1024&seed=42"

# 3. دالة التوليد الذكية (تحديث الأسماء التقنية)
def smart_generate(contents):
    # قائمة الموديلات بناءً على صورتك الأخيرة في AI Studio
    models_to_try = [
        "gemini-3-pro-preview",    # الموديل الذي ظهر في صورتك السادسة
        "gemini-1.5-flash",        # الموديل الاحتياطي المستقر
    ]
    
    for m_name in models_to_try:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(contents)
            return response.text, m_name
        except:
            continue
    return "🚫 لم نتمكن من الاتصال بالموديل حالياً.", None

# 4. واجهة التحكم الجانبية (إعادة الميكروفون والصور)
with st.sidebar:
    st.header("🎨 أدوات التحكم")
    audio_record = mic_recorder(start_prompt="تحدث الآن 🎤", stop_prompt="إرسال 📤", key='recorder')
    st.divider()
    uploaded_file = st.file_uploader("رفع صورة لتحليلها:", type=["jpg", "png", "jpeg"])
    if st.button("🗑️ مسح الذاكرة"):
        st.session_state.messages = []
        st.rerun()

# 5. الواجهة الرئيسية
st.title("⚡ مساعد مصعب المتكامل")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img_url" in msg: st.image(msg["img_url"])

# 6. معالجة الطلبات
user_input = st.chat_input("اطلب رسم صورة أو اسأل سؤالاً...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل المحتوى"
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner("جاري التفكير والرسم..."):
            contents = [prompt]
            if uploaded_file: contents.append(Image.open(uploaded_file))
            if current_audio: contents.append({"mime_type": "audio/wav", "data": current_audio})
            
            raw_text, used_model = smart_generate(contents)
            
            if used_model:
                # تنظيف الرد من أكواد JSON و "Thought" التي تظهر في صورك
                clean_answer = re.sub(r'\{.*?\}', '', raw_text, flags=re.DOTALL)
                clean_answer = re.sub(r'thought:.*', '', clean_answer, flags=re.IGNORECASE).strip()

                # ميزة الرسم التلقائي
                img_url = None
                if any(x in prompt for x in ["ارسم", "صورة", "تخيل", "draw", "image"]):
                    img_url = draw_image(prompt)
                    st.image(img_url, caption="الصورة التي رسمتها لك")

                st.markdown(clean_answer if clean_answer else "تفضل الصورة التي طلبتها:")
                st.caption(f"🤖 المحرك: {used_model}")
                
                # الرد الصوتي
                try:
                    tts = gTTS(text=clean_answer[:200] if clean_answer else "تفضل", lang='ar')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, autoplay=True)
                except: pass
                
                new_msg = {"role": "assistant", "content": clean_answer}
                if img_url: new_msg["img_url"] = img_url
                st.session_state.messages.append(new_msg)
