import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image

# إعداد الصفحة
st.set_page_config(page_title="مصعب AI المتكامل", page_icon="🤖", layout="wide")

# تحميل مفتاح الـ API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("يرجى إضافة GEMINI_API_KEY في الإعدادات.")
    st.stop()

genai.configure(api_key=api_key)

# --- القائمة الجانبية (الإعدادات) ---
with st.sidebar:
    st.title("⚙️ الإعدادات")
    
    persona = st.selectbox("الشخصية:", ["مساعد عام", "خبير برمجيات", "مدرس لغات", "محلل بيانات"])
    
    model_choice = st.radio(
        "اختر المحرك:",
        ["gemini-2.5-flash", "gemma-3-27b-it", "توليد الصور (Imagen 3)"]
    )
    
    uploaded_file = st.file_uploader("ارفع صورة للتحليل:", type=["jpg", "jpeg", "png"])
    
    if st.button("حذف سجل المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- منطق عمل توليد الصور ---
if model_choice == "توليد الصور (Imagen 3)":
    st.header("🎨 صانع الصور الذكي")
    prompt = st.text_area("صف الصورة بالإنجليزية:", placeholder="Example: A smart robot fixing a computer...")
    if st.button("إبدأ الرسم 🖌️"):
        if prompt:
            with st.spinner("جاري الرسم..."):
                try:
                    model = genai.GenerativeModel("imagen-3.0-generate-001")
                    result = model.generate_content(prompt)
                    st.image(result.candidates[0].content.parts[0].inline_data.data, caption="النتيجة")
                except Exception as e:
                    st.error(f"حدث خطأ: {e}")
        else:
            st.warning("اكتب وصفاً أولاً.")

# --- منطق عمل الدردشة وتحليل الصور ---
else:
    st.header(f"💬 الدردشة ({model_choice}) - {persona}")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("اسأل أي شيء..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("جاري المعالجة..."):
                try:
                    model = genai.GenerativeModel(model_choice)
                    full_prompt = [f"تقمص دور {persona}: {prompt}"]
                    
                    if uploaded_file:
                        img = Image.open(uploaded_file)
                        full_prompt.append(img)
                    
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"خطأ: {e}")
