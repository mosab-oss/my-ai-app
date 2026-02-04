import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
import io, urllib.parse, re, json, os
from PIL import Image

# 1. الإعدادات والاتصال
st.set_page_config(page_title="منصة مصعب الشاملة V11.5", layout="wide", page_icon="💎")

api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ المفتاح ناقص في Secrets!")
    st.stop()

# دالة الرسم (تستخدم الطلب المختصر لضمان عدم كسر الرابط)
def draw_image(user_query):
    # تنظيف الطلب: نأخذ الكلمات فقط ونحذف الرموز
    clean_query = re.sub(r'[^\w\s]', '', user_query)[:100]
    encoded = urllib.parse.quote(clean_query)
    return f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&seed=42"

# 2. التبديل التلقائي بين المحركات
def generate_smart_response(contents):
    model_hierarchy = ["gemini-3-pro-preview", "gemma-3-27b-it", "gemini-2.5-flash-exp"]
    for m_name in model_hierarchy:
        try:
            model = genai.GenerativeModel(m_name)
            response = model.generate_content(contents)
            if response and response.text:
                return response.text, m_name
        except: continue
    return None, None

# 3. الواجهة الجانبية (Sidebar)
with st.sidebar:
    st.header("⚙️ إعدادات V11.5")
    persona = st.selectbox("اختر التخصص:", ["مساعد ذكي عام", "خبير برمجة وتطوير", "مدرس لغات محترف", "مصمم صور إبداعي"])
    
    persona_instr = {
        "خبير برمجة وتطوير": "أنت خبير Ubuntu. قدم كوداً مشروحاً.",
        "مدرس لغات محترف": "أنت مدرس لغات. صحح الأخطاء واشرح القواعد.",
        "مصمم صور إبداعي": "أنت فنان رقمي. ركز على الوصف الجمالي.",
        "مساعد ذكي عام": "أنت مساعد شامل."
    }
    
    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')
    uploaded_file = st.file_uploader("رفع صورة:", type=['jpg', 'png', 'jpeg'])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 4. إدارة الرسائل
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img_url" in msg and msg["img_url"]:
            st.image(msg["img_url"])

# 5. التنفيذ (إصلاح مشكلة عدم ظهور الصورة)
user_input = st.chat_input("اطلب ما تشاء من مصعب...")

if user_input or audio_record or uploaded_file:
    prompt = user_input if user_input else "تحليل المحتوى المرفق"
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("جاري التفكير والرسم..."):
            contents = [f"تعليماتك: {persona_instr[persona]}\n\nطلب المستخدم: {prompt}"]
            if uploaded_file: contents.append(Image.open(uploaded_file))
            
            raw_text, used_model = generate_smart_response(contents)
            
            if raw_text:
                img_url = None
                # الشرط الصحيح: نستخدم (prompt) الذي كتبه المستخدم للرسم وليس (raw_text)
                if any(x in prompt for x in ["ارسم", "صورة", "تخيل"]) or persona == "مصمم صور إبداعي":
                    img_url = draw_image(prompt) # هنا السر! نرسل طلبك المختصر وليس شرح Gemma الطويل
                    st.image(img_url, caption=f"تم الرسم بواسطة {used_model}")
                
                st.markdown(raw_text)
                st.session_state.messages.append({"role": "assistant", "content": raw_text, "img_url": img_url})
