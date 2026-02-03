import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import re

# 1. إعدادات الصفحة والبيئة
st.set_page_config(page_title="مساعد مصعب المتكامل V2", layout="wide", page_icon="🎨")
load_dotenv()

# 2. إعداد الاتصال بمفتاح الـ API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ لم يتم العثور على المفتاح. أضفه في ملف .env باسم GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=api_key)

# 3. دالة التوليد الذكية (تجاوز الأخطاء والتبديل التلقائي)
def smart_generate(contents):
    models_to_try = [
        "gemini-3-flash-preview",  # الموديل الذي ظهر في حسابك
        "gemini-2.0-flash-exp",    # الموديل البديل القوي
        "gemini-1.5-flash"         # الموديل الاحتياطي
    ]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            return response.text, model_name
        except Exception as e:
            if "404" in str(e) or "429" in str(e) or "quota" in str(e).lower():
                continue 
            else:
                return f"⚠️ خطأ تقني: {e}", None
    return "🚫 جميع المحركات مشغولة حالياً.", None

# 4. دالة النطق الصوتي
def speak(text):
    try:
        clean_text = re.sub(r'[*#_]', '', text[:250])
        tts = gTTS(text=clean_text, lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except:
        return None

# 5. القائمة الجانبية (صوت وصورة)
with st.sidebar:
    st.header("🎨 أدوات التحكم")
    st.subheader("🎙️ الميكروفون")
    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')
    
    st.divider()
    st.subheader("🖼️ تحليل الصور")
    uploaded_file = st.file_uploader("ارفع صورة لنحللها:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 6. الواجهة الرئيسية وعرض المحتوى
st.title("⚡ مساعد مصعب المتكامل")
st.info("تم تفعيل ميزة إظهار الصور المولدة تلقائياً.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال المدخلات
user_input = st.chat_input("اطلب وصفاً أو صورة...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل المحتوى"
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner("جاري المعالجة..."):
            content_list = [prompt]
            if uploaded_file: content_list.append(Image.open(uploaded_file))
            if current_audio: content_list.append({"mime_type": "audio/wav", "data": current_audio})
            
            answer, used_model = smart_generate(content_list)
            
            if used_model:
                # --- ميزة ذكاء عرض الصور الجديدة ---
                # البحث عن أي روابط صور داخل الرد
                image_links = re.findall(r'(https?://\S+?\.(?:png|jpg|jpeg|gif))', answer)
                
                if image_links:
                    for link in image_links:
                        st.image(link, caption="تم توليدها بواسطة Gemini")
                
                # عرض النص الأصلي (سواء كان وصفاً أو كوداً)
                st.markdown(answer)
                st.caption(f"🤖 المحرك: {used_model}")
                
                # النطق الصوتي
                audio_fp = speak(answer)
                if audio_fp: st.audio(audio_fp, autoplay=True)
                
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                st.error(answer)
