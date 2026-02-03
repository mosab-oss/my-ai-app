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
st.set_page_config(page_title="مساعد مصعب المتكامل V3", layout="wide", page_icon="🌄")
load_dotenv()

# 2. إعداد الاتصال بمفتاح الـ API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ المفتاح غير موجود في ملف .env")
    st.stop()

genai.configure(api_key=api_key)

# 3. دالة التوليد الذكية (تجاوز الأخطاء والتبديل التلقائي)
def smart_generate(contents):
    # القائمة المحدثة بناءً على حسابك في AI Studio لتجنب خطأ 404
    models_to_try = [
        "gemini-3-flash-preview",  # الموديل التجريبي الجديد
        "gemini-2.0-flash-exp",    # الموديل البديل السريع
        "gemini-1.5-flash"         # الموديل الاحتياطي المستقر
    ]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            return response.text, model_name
        except Exception as e:
            # تخطي أخطاء الحصة (429) أو عدم وجود الموديل (404)
            if "404" in str(e) or "429" in str(e) or "quota" in str(e).lower():
                continue 
            else:
                return f"⚠️ خطأ تقني: {e}", None
    return "🚫 عذراً، جميع المحركات غير متاحة حالياً.", None

# 4. دالة معالجة الرد (لتحويل أكواد JSON إلى نصوص مفهومة)
def clean_response(text):
    # إذا حاول الموديل كتابة كود توليد صورة، نستخرج الوصف فقط
    if '"prompt":' in text:
        match = re.search(r'"prompt":\s*"([^"]+)"', text)
        if match:
            return f"🎨 **طلب توليد صورة:** {match.group(1)}"
    
    # تنظيف النصوص من الروابط الطويلة أو الأكواد المزعجة
    clean_text = re.sub(r'\{.*?\}', '', text, flags=re.DOTALL)
    return clean_text if clean_text.strip() else text

# 5. دالة النطق الصوتي
def speak(text):
    try:
        clean_for_audio = re.sub(r'[*#_]', '', text[:250])
        tts = gTTS(text=clean_for_audio, lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except:
        return None

# 6. واجهة التطبيق (القائمة الجانبية)
with st.sidebar:
    st.header("🎨 أدوات التحكم")
    st.subheader("🎙️ تسجيل صوتي")
    audio_record = mic_recorder(start_prompt="تحدث الآن 🎤", stop_prompt="إرسال 📤", key='recorder')
    
    st.divider()
    st.subheader("🖼️ تحليل الصور")
    uploaded_file = st.file_uploader("ارفع صورة لنحللها:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 7. الواجهة الرئيسية وعرض المحادثة
st.title("⚡ مساعد مصعب المتكامل")
st.info("تم تحديث الموديلات لتعمل مع Gemini 3 Preview ومعالجة الأكواد تلقائياً.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال المدخلات
user_input = st.chat_input("اكتب سؤالك أو اطلب صورة...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل المحتوى المرفق"
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner("جاري التفكير والتبديل بين المحركات..."):
            content_list = [prompt]
            if uploaded_file: content_list.append(Image.open(uploaded_file))
            if current_audio: content_list.append({"mime_type": "audio/wav", "data": current_audio})
            
            raw_answer, used_model = smart_generate(content_list)
            
            if used_model:
                # تنظيف الرد من الأكواد البرمجية قبل عرضه
                final_text = clean_response(raw_answer)
                
                st.markdown(final_text)
                st.caption(f"🤖 المحرك النشط: {used_model}")
                
                # الرد الصوتي
                audio_fp = speak(final_text)
                if audio_fp: st.audio(audio_fp, autoplay=True)
                
                st.session_state.messages.append({"role": "assistant", "content": final_text})
            else:
                st.error(raw_answer)
