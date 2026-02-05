import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re
from gtts import gTTS
from PIL import Image

# --- 1. الإعدادات والربط ---
st.set_page_config(page_title="منصة مصعب V16.2", layout="wide", page_icon="💎")

# ربط المحرك المحلي (LM Studio)
local_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# ربط محركات جوجل
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية (إضافة Gemma 3) ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.2")
    
    # القائمة المحدثة للمحركات
    engine_choice = st.selectbox(
        "🎯 اختر العقل المدبر:",
        [
            "DeepSeek R1 (محلي - Offline)", 
            "Gemini 2.5 Flash (الأسرع)", 
            "Gemma 3 27B IT (الوسط الذكي)", # الإضافة الجديدة
            "Gemini 3 Pro (الأذكى)", 
            "Imagen 3 (توليد صور)"
        ]
    )
    
    # خريطة الموديلات البرمجية الدقيقة
    model_map = {
        "Gemini 2.5 Flash (الأسرع)": "gemini-2.5-flash-exp",
        "Gemma 3 27B IT (الوسط الذكي)": "gemma-3-27b-it", # تم التحديث هنا
        "Gemini 3 Pro (الأذكى)": "gemini-3-pro-preview"
    }
    
    st.divider()
    
    persona = st.selectbox("👤 شخصية المساعد:", ["مساعد مبرمج", "خبير لغوي", "محلل ذكي"])
    uploaded_file = st.file_uploader("📸 رفع صورة للتحليل:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- 3. الدوال الذكية ---
def clean_think_tags(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=st.DOTALL).strip()

# --- 4. واجهة الدردشة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(clean_think_tags(msg["content"]))

# --- 5. معالجة الطلبات ---
if prompt := st.chat_input("تحدث مع المحرك المختار..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        full_response = ""
        
        # أ. وضع DeepSeek المحلي
        if "DeepSeek" in engine_choice:
            try:
                res = local_client.chat.completions.create(
                    model="deepseek-r1-distill-qwen-7b",
                    messages=[{"role": "system", "content": f"أنت {persona}"}, {"role": "user", "content": prompt}],
                    stream=True
                )
                placeholder = st.empty()
                for chunk in res:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        placeholder.markdown(full_response + "▌")
                placeholder.markdown(clean_think_tags(full_response))
            except:
                st.error("تأكد من تشغيل السيرفر المحلي!")

        # ب. وضع محركات جوجل (Gemini & Gemma)
        elif any(name in engine_choice for name in ["Gemini", "Gemma"]):
            try:
                selected_model = model_map[engine_choice]
                model = genai.GenerativeModel(selected_model)
                
                if uploaded_file:
                    img = Image.open(uploaded_file)
                    res = model.generate_content([prompt, img])
                else:
                    res = model.generate_content(prompt)
                
                full_response = res.text
                st.markdown(full_response)
            except Exception as e:
                st.error(f"خطأ في الاتصال: {e}")

        # ج. وضع الصوت التلقائي
        if full_response:
            audio_text = clean_think_tags(full_response)
            try:
                tts = gTTS(text=audio_text[:300], lang='ar')
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                st.audio(audio_io)
            except: pass
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
