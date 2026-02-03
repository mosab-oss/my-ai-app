import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
from streamlit_mic_recorder import mic_recorder
import urllib.parse

# 1. إعدادات الصفحة
st.set_page_config(page_title="مساعد مصعب المتكامل", layout="wide")

# جلب المفتاح من Secrets (الذي وضعتَه في الصورة رقم 9)
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("المفتاح غير موجود في Secrets!")

# دالة الرسم (لتحويل طلباتك إلى صور حقيقية)
def draw_image(description):
    encoded = urllib.parse.quote(description)
    return f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&seed=42"

st.title("⚡ مساعد مصعب المتكامل")

# القائمة الجانبية
with st.sidebar:
    st.header("🎨 أدوات التحكم")
    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')
    uploaded_file = st.file_uploader("ارفع صورة:", type=["jpg", "png", "jpeg"])

if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض المحادثة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img_url" in msg:
            st.image(msg["img_url"])

# معالجة الإدخال
user_input = st.chat_input("اطلب رسم صورة أو اسأل سؤالاً...")

if user_input or uploaded_file:
    prompt = user_input if user_input else "حلل هذه الصورة"
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # التغيير الجوهري: استخدام الاسم الصحيح للموديل المتاح لك
            model = genai.GenerativeModel("gemini-3-pro-preview")
            
            content_list = [prompt]
            if uploaded_file:
                content_list.append(Image.open(uploaded_file))
            
            response = model.generate_content(content_list)
            answer = response.text
            
            # ميزة الرسم: إذا طلبت صورة، سيظهرها التطبيق فوراً
            img_url = None
            if any(word in prompt for word in ["ارسم", "صورة", "تخيل"]):
                img_url = draw_image(prompt)
                st.image(img_url, caption="تم رسم الصورة بنجاح!")

            st.markdown(answer)
            
            # حفظ في الذاكرة
            msg_data = {"role": "assistant", "content": answer}
            if img_url:
                msg_data["img_url"] = img_url
            st.session_state.messages.append(msg_data)
            
        except Exception as e:
            st.error(f"حدث خطأ: {e}")
            st.info("تأكد أن الموديل gemini-3-pro-preview مفعّل في حسابك.")
