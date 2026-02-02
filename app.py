import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image

# 1. إعدادات المفتاح والبيئة
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 2. دالة التوليد الذكية (تنتقل بين الموديلات تلقائياً)
def generate_content_with_fallback(contents):
    # قائمة الموديلات حسب الأولوية
    models_to_try = ["gemini-3-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(contents)
            return response.text, model_name  # نعيد النص واسم الموديل الذي نجح
        except Exception as e:
            # إذا كان الخطأ هو انتهاء الحصة (429)، نجرب الموديل التالي
            if "429" in str(e) or "quota" in str(e).lower():
                continue 
            else:
                return f"خطأ تقني: {e}", None
    
    return "عذراً، انتهت حصة جميع الموديلات المتاحة لليوم.", None

# 3. واجهة التطبيق المبسطة
st.title("🚀 مساعد مصعب الذكي (المضاد للتوقف)")

if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض المحادثة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# إدخال المستخدم
user_input = st.chat_input("اسألني أي شيء...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("جاري التفكير (نبحث عن موديل متاح)..."):
            # محاولة التوليد مع خاصية الـ Fallback
            answer, successful_model = generate_content_with_fallback([user_input])
            
            if successful_model:
                st.markdown(answer)
                st.caption(f"تمت الإجابة بواسطة محرك: {successful_model}")
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                st.error(answer)
