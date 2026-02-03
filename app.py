import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io
import urllib.parse
import re

# 1. إعدادات الصفحة
st.set_page_config(page_title="مساعد مصعب الذكي", layout="wide", page_icon="⚡")

# جلب المفتاح من Secrets
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ المفتاح غير موجود في Secrets!")
    st.stop()

# دالة الرسم
def draw_image(description):
    encoded = urllib.parse.quote(description)
    return f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&seed=42"

# 2. القائمة الجانبية: إضافة اختيار التخصص
with st.sidebar:
    st.header("⚙️ إعدادات المساعد")
    
    # ميزة اختيار الشخصية (التي طلبتها)
    persona = st.selectbox(
        "اختر تخصص المساعد:",
        ["مساعد ذكي عام", "خبير برمجة وتطوير", "مدرس لغات محترف", "مصمم صور إبداعي"]
    )
    
    # تحديد تعليمات النظام (System Instructions) بناءً على الاختيار
    if persona == "خبير برمجة وتطوير":
        sys_instr = "أنت خبير برمجة عالمي. قدم كوداً نظيفاً واشرح المفاهيم البرمجية بتبسيط."
    elif persona == "مدرس لغات محترف":
        sys_instr = "أنت مدرس لغات خبير. صحح الأخطاء اللغوية وساعد المستخدم في ممارسة المحادثة."
    elif persona == "مصمم صور إبداعي":
        sys_instr = "أنت فنان رقمي. ركز على وصف الصور بدقة وحول طلبات المستخدم إلى لوحات فنية."
    else:
        sys_instr = "أنت مساعد ذكي شامل ومفيد."

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
st.caption(f"يعمل الآن بواسطة: Gemini 3 Pro Preview")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img_url" in msg: st.image(msg["img_url"])

# 4. معالجة الطلبات
user_input = st.chat_input("اطلب ما تشاء...")
current_audio = audio_record['bytes'] if audio_record else None

if user_input or current_audio or uploaded_file:
    prompt = user_input if user_input else "حلل هذا المرفق"
    
    with st.chat_message("user"):
        st.markdown(prompt)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner(f"جاري التفكير كـ {persona}..."):
            # محاولة استخدام الموديلات بالتوالي لتجنب خطأ Quota (الصورة 10)
            models_to_try = ["gemini-3-pro-preview", "gemini-1.5-flash"]
            raw_text = ""
            used_model = ""
            
            # دمج تعليمات التخصص مع طلب المستخدم
            full_prompt = f"إرشاداتك: {sys_instr}\n\nطلب المستخدم: {prompt}"
            
            contents = [full_prompt]
            if uploaded_file: contents.append(Image.open(uploaded_file))
            if current_audio: contents.append({"mime_type": "audio/wav", "data": current_audio})
            
            for m_name in models_to_try:
                try:
                    model = genai.GenerativeModel(m_name)
                    response = model.generate_content(contents)
                    raw_text = response.text
                    used_model = m_name
                    break
                except:
                    continue

            if used_model:
                # تنظيف الرد
                clean_answer = re.sub(r'\{.*?\}', '', raw_text, flags=re.DOTALL)
                clean_answer = re.sub(r'thought:.*', '', clean_answer, flags=re.IGNORECASE).strip()

                # الرسم التلقائي
                img_url = None
                if any(x in prompt for x in ["ارسم", "صورة", "تخيل"]) or persona == "مصمم صور إبداعي":
                    img_url = draw_image(prompt)
                    st.image(img_url, caption="الصورة الناتجة")

                st.markdown(clean_answer)
                
                # الرد الصوتي
                try:
                    tts = gTTS(text=clean_answer[:200], lang='ar')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, autoplay=True)
                except: pass
                
                new_msg = {"role": "assistant", "content": clean_answer}
                if img_url: new_msg["img_url"] = img_url
                st.session_state.messages.append(new_msg)
            else:
                st.error("⚠️ الموديلات لا تستجيب حالياً، يرجى المحاولة بعد قليل.")
