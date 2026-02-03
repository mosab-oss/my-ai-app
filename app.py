import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import re

# 1. إعدادات الصفحة
st.set_page_config(page_title="مساعد مصعب الذكي - نسخة الصور", layout="wide", page_icon="🖼️")
load_dotenv()

# 2. إعداد المفتاح
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 3. دالة التوليد (الموديلات المتاحة في حسابك)
def smart_generate(contents):
    models = ["gemini-3-flash-preview", "gemini-2.0-flash-exp", "gemini-1.5-flash"]
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(contents)
            return response.text, m
        except:
            continue
    return "🚫 خطأ في الاتصال.", None

# --- الواجهة ---
st.title("⚡ مساعد مصعب المتكامل")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')
    uploaded_file = st.file_uploader("ارفع صورة:", type=["jpg", "png", "jpeg"])

# عرض المحادثة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال المدخلات
user_input = st.chat_input("اطلب رسم صورة أو اسأل سؤالاً...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل هذا"
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("جاري التوليد..."):
            content_list = [prompt]
            if uploaded_file: content_list.append(Image.open(uploaded_file))
            if current_audio: content_list.append({"mime_type": "audio/wav", "data": current_audio})
            
            raw_answer, used_model = smart_generate(content_list)
            
            if used_model:
                # --- السحر هنا: البحث عن رابط الصورة وعرضه فوراً ---
                # هذا الجزء يبحث عن أي رابط يبدأ بـ http وينتهي بصيغة صورة
                img_match = re.search(r'(https?://\S+?\.(?:png|jpg|jpeg|gif))', raw_answer)
                
                if img_match:
                    image_url = img_match.group(1)
                    st.image(image_url, caption="تم توليد الصورة بنجاح!")
                
                # تنظيف النص من أكواد الـ JSON المزعجة للعرض فقط
                clean_text = re.sub(r'\{.*?\}', '🎨 جاري معالجة طلب الصورة...', raw_answer, flags=re.DOTALL)
                
                st.markdown(clean_text)
                st.caption(f"🤖 المحرك: {used_model}")
                
                # الرد الصوتي
                try:
                    tts = gTTS(text=clean_text[:200], lang='ar')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp, autoplay=True)
                except: pass
                
                st.session_state.messages.append({"role": "assistant", "content": clean_text})
