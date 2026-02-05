import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re
from gtts import gTTS
from PIL import Image

# 1. الإعدادات والربط
st.set_page_config(page_title="منصة مصعب v16.3", layout="wide", page_icon="💎")

local_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# 2. القائمة الجانبية (إعادة المدرس اللغوي)
with st.sidebar:
    st.header("🎮 مركز التحكم")
    
    engine_choice = st.selectbox(
        "🎯 اختر المحرك:",
        ["DeepSeek R1 (محلي)", "Gemini 2.5 Flash", "Gemma 3 27B", "Gemini 3 Pro"]
    )
    
    # هنا عاد المدرس اللغوي الذي سألت عنه
    persona = st.selectbox("👤 شخصية المساعد:", ["مدرس لغوي", "مساعد مبرمج", "محلل ذكي"])
    
    uploaded_file = st.file_uploader("📸 تحليل الصور (لـ Gemini):", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# 3. تنظيف ردود DeepSeek (لحل مشكلة <think>)
def clean_response(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=st.DOTALL).strip()

# 4. واجهة الدردشة
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(clean_response(msg["content"]))

# 5. المعالجة
if prompt := st.chat_input("تحدث مع المدرس اللغوي أو المبرمج..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        full_response = ""
        
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
                placeholder.markdown(clean_response(full_response))
            except: st.error("تأكد من تشغيل LM Studio!")

        else: # محركات جوجل
            try:
                # استخدام الموديل الأحدث لتجنب خطأ 404
                model_name = "gemini-1.5-flash-latest" 
                model = genai.GenerativeModel(model_name)
                res = model.generate_content([prompt, Image.open(uploaded_file)] if uploaded_file else prompt)
                full_response = res.text
                st.markdown(full_response)
            except Exception as e:
                st.error(f"خطأ في الاتصال: {e}")

        # الصوت
        if full_response:
            try:
                tts = gTTS(text=clean_response(full_response)[:300], lang='ar')
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                st.audio(audio_io)
            except: pass
            st.session_state.messages.append({"role": "assistant", "content": full_response})
