import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import urllib.parse
import re
import json

# 1. إعدادات الصفحة والاتصال
st.set_page_config(page_title="منصة مصعب الشاملة", layout="wide", page_icon="💎")

# جلب المفتاح من Secrets
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

# 2. القائمة الجانبية: التخصصات، الأدوات، وتحميل المحادثة
with st.sidebar:
    st.header("⚙️ إعدادات المساعد")
    
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
    
    st.divider()
    # ميزة تحميل ومسح المحادثة (كما في صورتك 17)
    if "messages" in st.session_state and st.session_state.messages:
        # زر تحميل المحادثة
        chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        st.download_button(label="📥 تحميل المحادثة", data=chat_text, file_name="mosab_chat.txt", mime="text/plain")
        
        # زر مسح المحادثة
        if st.button("🗑️ مسح المحادثة"):
            st.session_state.messages = []
            st.rerun()

# 3. الواجهة الرئيسية
st.title(f"💎 {persona}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img_url" in msg: st.image(msg["img_url"])

# 4. نظام "الانتقال التلقائي" الشامل (Hierarchy)
def generate_smart_response(contents):
    # ترتيب الموديلات لضمان الاستجابة غداً وكل يوم
    model_hierarchy = [
        "gemini-3-pro-preview",   
        "gemma-3-27b-it",         
        "gemini-2.5-flash-exp",   
        "gemini-1.5-flash"
    ]
    
    for m_name in model_hierarchy:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(contents)
            if response and response.text:
                return response.text, m_name
        except:
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
        with st.spinner(f"جاري البحث عن محرك متاح..."):
            
            full_prompt = f"تعليماتك: {persona_instr[persona]}\n\nطلب المستخدم: {prompt}"
            contents = [full_prompt]
            if uploaded_file: contents.append(Image.open(uploaded_file))
            if current_audio: contents.append({"mime_type": "audio/wav", "data": current_audio})
            
            raw_text, used_model = generate_smart_response(contents)
            
            if raw_text:
                # تنظيف الرد من الـ Thought (الذي ظهر في صورتك 1)
                clean_answer = re.sub(r'\{.*?\}', '', raw_text, flags=re.DOTALL)
                clean_answer = re.sub(r'thought:.*', '', clean_answer, flags=re.IGNORECASE).strip()

                img_url = None
                if any(x in prompt for x in ["ارسم", "صورة", "تخيل"]) or persona == "مصمم صور إبداعي":
                    img_url = draw_image(prompt)
                    st.image(img_url, caption=f"تم التوليد بواسطة {used_model}")

                st.markdown(clean_answer)
                st.caption(f"🚀 المحرك النشط: {used_model}")
                
                # الرد الصوتي الآلي
                try:
                    tts = gTTS(text=clean_answer[:200], lang='ar')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, autoplay=True)
                except: pass
                
                st.session_state.messages.append({"role": "assistant", "content": clean_answer, "img_url": img_url})
            else:
                st.error("❌ جميع المحركات استهلكت حصتها اليومية.")
