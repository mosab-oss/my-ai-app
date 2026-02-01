import streamlit as st
import requests
import os
import base64
import logging
from dotenv import load_dotenv

# 1. إعداد التسجيل والبيئة
logging.basicConfig(level=logging.INFO)
load_dotenv()

# التحقق من وجود المفتاح قبل البدء
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    st.error("❌ لم يتم العثور على API_KEY في ملف .env")
    st.stop()

# --- 2. فصل المهام إلى دوال (Functions) ---

def encode_image_to_base64(uploaded_file):
    """تحويل الصورة إلى نص مشفر لإرسالها للـ API"""
    try:
        return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
    except Exception as e:
        logging.error(f"خطأ في معالجة الصورة: {e}")
        return None

def build_message(prompt, persona_name, encoded_image=None, mime_type=None):
    """بناء هيكل الرسالة المطلوب من جوجل"""
    system_instructions = {
        "مهندس برمجيات محترف": "أنت خبير برمجة، أجب بكود نظيف وشرح تقني.",
        "مدرس لغات": "أنت مدرس لغة ودود، صحح الأخطاء واشرح القواعد.",
        "مساعد عام": "أنت مساعد ذكي ولطيف."
    }
    
    instruction = system_instructions.get(persona_name, "")
    full_text = f"{instruction}\n\nالسؤال: {prompt}"
    
    parts = [{"text": full_text}]
    
    if encoded_image:
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": encoded_image
            }
        })
    
    return {"role": "user", "parts": parts}

# --- 3. واجهة المستخدم ---

st.set_page_config(page_title="منصة مصعب الاحترافية", layout="wide")

with st.sidebar:
    st.title("⚙️ الإعدادات")
    persona = st.selectbox("الشخصية:", ["مساعد عام", "مهندس برمجيات محترف", "مدرس لغات"])
    model_choice = st.radio("المحرك:", ["gemini-2.5-flash", "gemma-3-27b-it"], index=0)
    uploaded_file = st.file_uploader("ارفع صورة:", type=["png", "jpg", "jpeg"])
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

st.title(f"🚀 {model_choice}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الدردشة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["parts"][0]["text"])

# منطقة الإدخال
if prompt := st.chat_input("اسألني أي شيء..."):
    with st.chat_message("user"):
        st.markdown(prompt)

    # معالجة الصورة إن وجدت
    encoded_img = encode_image_to_base64(uploaded_file) if uploaded_file else None
    
    # بناء الرسالة وإضافتها للذاكرة
    user_msg = build_message(prompt, persona, encoded_img, uploaded_file.type if uploaded_file else None)
    st.session_state.messages.append(user_msg)

    # الاتصال بالـ API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_choice}:generateContent?key={API_KEY}"
    
    try:
        with st.spinner("جاري التفكير..."):
            response = requests.post(url, json={"contents": st.session_state.messages})
            response.raise_for_status()
            result = response.json()
            
            answer = result['candidates'][0]['content']['parts'][0]['text']
            with st.chat_message("model"):
                st.markdown(answer)
            st.session_state.messages.append({"role": "model", "parts": [{"text": answer}]})
            
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ خطأ في الاتصال: تأكد من الكوتا أو اتصال الإنترنت.")
        logging.exception("API Call Failed")
