import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image
from gtts import gTTS
import io

# 1. إعدادات البداية
st.set_page_config(page_title="مصعب AI - النسخة السينمائية", layout="wide")
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 2. محرك الرسم المطور (يحول وصفك البسيط إلى لوحة سينمائية)
def draw_smart_image(user_prompt):
    try:
        # هنا نستخدم Gemini 3 Flash ليقوم بدور "كاتب السيناريو" ويحسن الوصف
        desc_model = genai.GenerativeModel("gemini-3-flash-preview")
        enhancer_prompt = f"Convert this image description into a highly detailed cinematic prompt for Imagen 3: {user_prompt}"
        enhanced_prompt = desc_model.generate_content(enhancer_prompt).text
        
        # الآن نرسل الوصف المطور لمحرك الرسم Imagen
        # ملاحظة: إذا لم ينجح imagen-3، جرب استبداله بـ "imagen-3.0-generate-001"
        paint_model = genai.GenerativeModel("imagen-3.0-generate-001")
        response = paint_model.generate_content(enhanced_prompt)
        
        # التحقق من استلام بيانات الصورة
        if response.candidates[0].content.parts[0].inline_data:
            return response.candidates[0].content.parts[0].inline_data.data
        return "وصف"
    except Exception as e:
        return f"error: {e}"

# 3. وظيفة الصوت (الرد الذكي)
def speak(text):
    tts = gTTS(text=text.replace('*', '').replace('#', ''), lang='ar')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp

# 4. واجهة المستخدم
with st.sidebar:
    st.header("🎨 خيارات المحرك")
    mode = st.radio("اختر الوضع:", ["دردشة ورؤية 👁️", "رسم احترافي 🖌️"])
    st.divider()
    st.subheader("🖼️ قسم الرؤية (Vision)")
    uploaded_file = st.file_uploader("ارفع صورة لتحليلها:", type=["jpg", "png"])
    if st.button("🗑️ مسح الذاكرة"):
        st.session_state.messages = []
        st.rerun()

st.title("⚡ مساعد مصعب المتكامل")

# --- منطق الرسم الاحترافي ---
if mode == "رسم احترافي 🖌️":
    prompt = st.text_input("صف ما تريد رسمه (بالعربي أو الإنجليزي):")
    if st.button("توليد اللوحة الفنية"):
        with st.spinner("جاري تحسين الوصف والرسم..."):
            result = draw_smart_image(prompt)
            if isinstance(result, str) and "error" in result:
                st.error("المحرك يحتاج VPN أمريكي للرسم البرمجي.")
            elif result == "وصف":
                st.warning("المحرك أعطى وصفاً فقط ولم يرسم. جرب تفعيل الـ VPN.")
            else:
                st.image(result, caption="تم التوليد بواسطة مصعب AI")

# --- منطق الدردشة والرؤية الشامل ---
else:
    if "messages" not in st.session_state: st.session_state.messages = []
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    user_msg = st.chat_input("اسألني عن الصورة أو دردش...")
    
    if user_msg or uploaded_file:
        with st.chat_message("user"):
            st.write(user_msg if user_msg else "حلل هذه الصورة")
            if uploaded_file: st.image(uploaded_file, width=300)
            
        with st.chat_message("assistant"):
            try:
                model = genai.GenerativeModel("gemini-3-flash-preview")
                content = [user_msg if user_msg else "ماذا ترى في هذه الصورة؟"]
                if uploaded_file: content.append(Image.open(uploaded_file))
                
                response = model.generate_content(content)
                st.write(response.text)
                st.audio(speak(response.text), autoplay=True)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e: st.error(f"خطأ: {e}")
