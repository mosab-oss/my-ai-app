import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from gtts import gTTS
import io

# 1. إعداد الصفحة والمفتاح
st.set_page_config(page_title="مصعب AI المتكامل", layout="wide")
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 2. وظيفة الرسم (المبسطة لتجاوز التعارض)
def draw_image(prompt):
    try:
        # استخدام الموديل الموحد المتوافق مع جيل Gemini 3
        model = genai.GenerativeModel("imagen-3.0-generate-001")
        response = model.generate_content(prompt)
        return response.candidates[0].content.parts[0].inline_data.data
    except Exception as e:
        return f"error: {e}"

# 3. وظيفة الصوت
def speak(text):
    tts = gTTS(text=text.replace('*', ''), lang='ar')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp

# 4. واجهة المستخدم (الرؤية في القائمة الجانبية)
with st.sidebar:
    st.header("🖼️ قسم الرؤية (Vision)")
    uploaded_file = st.file_uploader("ارفع صورة لتحليلها:", type=["jpg", "png"])
    st.divider()
    mode = st.radio("ماذا تريد أن أفعل؟", ["دردشة ورؤية 💬", "رسم صور 🎨"])

# 5. منطق التشغيل
st.title("🚀 مساعد مصعب الذكي")

if mode == "رسم صور 🎨":
    prompt = st.text_input("صف الصورة بالإنجليزية:")
    if st.button("ارسم الآن"):
        with st.spinner("جاري الرسم..."):
            result = draw_image(prompt)
            if isinstance(result, str) and "error" in result:
                st.error("عذراً، محرك الرسم يحتاج VPN أمريكي ليعمل برمجياً.")
            else:
                st.image(result)

else: # وضع الدردشة والرؤية
    user_msg = st.chat_input("اسأل عن الصورة أو دردش...")
    if user_msg or uploaded_file:
        with st.chat_message("user"):
            st.write(user_msg if user_msg else "حلل هذه الصورة")
            if uploaded_file: st.image(uploaded_file, width=300)
        
        with st.chat_message("assistant"):
            model = genai.GenerativeModel("gemini-3-flash-preview")
            content = [user_msg if user_msg else "ماذا يوجد في الصورة؟"]
            if uploaded_file: content.append(Image.open(uploaded_file))
            
            response = model.generate_content(content)
            st.write(response.text)
            st.audio(speak(response.text), autoplay=True)
