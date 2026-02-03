import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
import re

# 1. إعدادات الصفحة والاتصال
st.set_page_config(page_title="مساعد مصعب المتكامل", layout="wide", page_icon="⚡")

# تأكد من وضع المفتاح هنا أو في Secrets
api_key = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 2. دالة التوليد الذكية
def generate_content_with_image(prompt):
    # محاولة استخدام الموديل الموضح في صورتك
    model_name = "gemini-3-flash-preview"
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text, model_name
    except Exception as e:
        return f"خطأ: {str(e)}", None

# 3. واجهة المستخدم
st.title("⚡ مساعد مصعب المتكامل")

if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض المحادثة السابقة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال الطلب الجديد
user_input = st.chat_input("اطلب رسم صورة أو اسأل سؤالاً...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    
    with st.chat_message("assistant"):
        with st.spinner("جاري التوليد..."):
            answer, m_used = generate_content_with_image(user_input)
            
            # --- الجزء الأهم: استخراج وعرض الصورة ---
            # البحث عن أي رابط ينتهي بامتداد صورة داخل النص
            image_urls = re.findall(r'(https?://\S+?\.(?:png|jpg|jpeg|gif))', answer)
            
            if image_urls:
                for url in image_urls:
                    st.image(url, caption="الصورة المولدة")
            
            # تنظيف النص من الأكواد البرمجية المزعجة (JSON) وعرض النص المفيد فقط
            clean_answer = re.sub(r'\{.*?\}', '', answer, flags=re.DOTALL).strip()
            if not clean_answer: clean_answer = "تم توليد الصورة بناءً على طلبك."
            
            st.markdown(clean_answer)
            st.caption(f"🤖 المحرك: {m_used}")
            
            st.session_state.messages.append({"role": "assistant", "content": clean_answer})
