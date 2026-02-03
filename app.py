import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import urllib.parse
import re

# 1. إعدادات الصفحة والاتصال
st.set_page_config(page_title="مساعد مصعب الذكي", layout="wide", page_icon="⚡")

# جلب المفتاح من Secrets (الذي تأكدنا منه في صورتك رقم 9)
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ المفتاح غير موجود في Secrets!")
    st.stop()

# دالة الرسم الإبداعي
def draw_image(description):
    encoded = urllib.parse.quote(description)
    return f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&seed=42"

# 2. القائمة الجانبية: التخصصات والأدوات
with st.sidebar:
    st.header("⚙️ إعدادات المساعد")
    
    # ميزة اختيار التخصص (التي طلبتها)
    persona = st.selectbox(
        "اختر تخصص المساعد:",
        ["مساعد ذكي عام", "خبير برمجة وتطوير", "مدرس لغات محترف", "مصمم صور إبداعي"]
    )
    
    persona_instr = {
        "خبير برمجة وتطوير": "أنت خبير برمجة. قدم حلولاً برمجية واضحة واشرح الكود بالعربي.",
        "مدرس لغات محترف": "أنت مدرس لغات. صحح القواعد وساعد في تعلم كلمات جديدة.",
        "مصمم صور إبداعي": "أنت فنان رقمي. ركز على الوصف البصري لإنتاج أفضل الصور.",
        "مساعد ذكي عام": "أنت مساعد شامل تجيب بدقة على كافة الأسئلة."
    }

    st.divider()
    st.subheader("🎙️ التسجيل الصوتي")
    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')
    
    st.divider()
    uploaded_file = st.file_uploader("رفع صورة:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح الذاكرة"):
        st.session_state.messages = []
        st.rerun()

# 3. الواجهة الرئيسية
st.title(f"⚡ {persona}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img_url" in msg: st.image(msg["img_url"])

# 4. نظام "الانتقال التلقائي" المطور (The Core Logic)
def generate_smart_response(contents):
    # قائمة الموديلات مرتبة: Gemini 3 (الأقوى) -> Gemini 2 (الأسرع) -> Gemini 1.5 (الاحتياطي)
    model_hierarchy = [
        "gemini-3-pro-preview", 
        "gemini-2.0-flash-exp", 
        "gemini-1.5-flash", 
        "gemini-1.5-pro"
    ]
    
    for m_name in model_hierarchy:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(contents)
            return response.text, m_name
        except Exception as e:
            # إذا حدث خطأ (مثل Quota Exceeded في صورتك 10)، سينتقل للموديل التالي تلقائياً
            continue
    return None, None

# 5. معالجة المدخلات
user_input = st.chat_input("اطلب ما تشاء...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل المحتوى المرفق"
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner(f"جاري اختيار أفضل محرك متاح للرد كـ {persona}..."):
            
            # دمج التخصص مع الطلب
            full_prompt = f"تعليماتك: {persona_instr[persona]}\n\nطلب المستخدم: {prompt}"
            
            contents = [full_prompt]
            if uploaded_file: contents.append(Image.open(uploaded_file))
            if current_audio: contents.append({"mime_type": "audio/wav", "data": current_audio})
            
            raw_text, used_model = generate_smart_response(contents)
            
            if raw_text:
                # تنظيف النص من أفكار الموديل (Thought) كما ظهر في صورك 1 و 2
                clean_answer = re.sub(r'\{.*?\}', '', raw_text, flags=re.DOTALL)
                clean_answer = re.sub(r'thought:.*', '', clean_answer, flags=re.IGNORECASE).strip()

                # ميزة الرسم التلقائي
                img_url = None
                if any(x in prompt for x in ["ارسم", "صورة", "تخيل"]) or persona == "مصمم صور إبداعي":
                    img_url = draw_image(prompt)
                    st.image(img_url, caption=f"تم التوليد بواسطة {used_model}")

                st.markdown(clean_answer)
                st.caption(f"🚀 المحرك النشط: {used_model}")
                
                # الرد الصوتي
                try:
                    tts = gTTS(text=clean_answer[:200], lang='ar')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, autoplay=True)
                except: pass
                
                st.session_state.messages.append({"role": "assistant", "content": clean_answer, "img_url": img_url})
            else:
                st.error("❌ عذراً مصعب، جميع المحركات (3.0 و 2.0 و 1.5) مشغولة حالياً أو انتهت حصتها اليومية.")
