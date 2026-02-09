import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, time, json
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 
from PIL import Image

# --- 1. إدارة الذاكرة ---
def load_history():
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f: return json.load(f)
    return []

st.set_page_config(page_title="تحالف مصعب v16.46.18", layout="wide", page_icon="🛡️")

# --- 2. القائمة الكاملة والنهائية للمحركات (بدون نواقص) ---
MODELS_GRID = {
    "Gemini 3 Flash (الجديد)": "gemini-3-flash",
    "Gemini 2.5 Flash (الذي تبحث عنه)": "gemini-2.5-flash", 
    "Gemini 2.0 Flash": "gemini-2.0-flash",
    "Gemini 1.5 Pro": "gemini-1.5-pro",
    "DeepSeek R1": "deepseek-reasoner",
    "Ernie 5.0": "ernie-5.0",
    "Kimi Latest": "moonshot-v1-8k"
}

# --- 3. زر مسح السجل (المثبت) ---
with st.sidebar:
    st.title("🛡️ مركز قيادة مصعب")
    if st.button("🧹 مسح السجل بالكامل", type="primary"):
        if os.path.exists("history.json"): os.remove("history.json")
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    persona = st.radio("👤 اختر الشخصية:", ["المدرس الذكي 👨‍🏫", "الخبير التقني 🛠️", "المساعد الشخصي 🤖"])
    # هنا تم تثبيت المحرك الذي سألت عنه
    engine_choice = st.selectbox("🎯 اختر العقل:", list(MODELS_GRID.keys()))
    st.divider()
    uploaded_file = st.file_uploader("🖼️ رفع وسائط", type=['jpg', 'png', 'csv'])

# --- 4. منطق الاستجابة (get_super_response) ---
def get_super_response(engine_label, user_input, persona_type, image=None):
    api_key = st.secrets.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    engine_id = MODELS_GRID[engine_label]
    
    try:
        if "Gemini" in engine_label:
            config = types.GenerateContentConfig(system_instruction=f"أنت {persona_type}")
            contents = [user_input]
            if image: contents.append(image)
            return client.models.generate_content(model=engine_id, contents=contents, config=config).text
        # إضافة منطق Kimi و Ernie هنا بنفس الطريقة السابقة...
    except Exception as e:
        return f"⚠️ خطأ في {engine_label}: {str(e)}"

# --- 5. الرادار وتحديث الواجهة ---
if "messages" not in st.session_state: st.session_state.messages = load_history()

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("تحدث مع Gemini 2.5 Flash الآن..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        response = get_super_response(engine_choice, prompt, persona)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
