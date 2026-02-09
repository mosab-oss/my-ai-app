import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, time, json, pandas as pd
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 
from PIL import Image

# --- 1. إدارة السجل والذاكرة (الميزة المفقودة سابقاً) ---
def load_history():
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def save_history(messages):
    with open("history.json", "w", encoding="utf-8") as f: 
        json.dump(messages, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="منصة مصعب السيادية v16.46.19", layout="wide", page_icon="🛡️")

# --- 2. قائمة المحركات السبعة (المثبتة بدون نقص) ---
MODELS_GRID = {
    "gemini-2.5-flash": "gemini-2.5-flash", 
    "gemini-2.0-flash": "gemini-2.0-flash",
    "gemini-3-pro-preview": "gemini-3-pro-preview", 
    "gemma-3-27b": "gemma-3-27b", 
    "deepseek-r1": "deepseek-reasoner", 
    "ernie-5.0": "ernie-5.0", 
    "kimi-latest": "moonshot-v1-8k"
}

# --- 3. تصميم الواجهة ---
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; background-color: #0e1117; color: white; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: monospace; }
    .stButton>button { width: 100%; background-color: #ff4b4b; color: white; } /* ستايل زر المسح */
    </style>
    """, unsafe_allow_html=True)

KEYS = {
    "GEMINI": st.secrets.get("GEMINI_API_KEY"),
    "ERNIE": st.secrets.get("ERNIE_API_KEY"),
    "KIMI": st.secrets.get("KIMI_API_KEY")
}

# --- 4. العقل الموجه (المنطق البرمجي لكل محرك) ---
def get_super_response(engine, user_input, persona, image=None, use_search=False):
    client_gem = genai.Client(api_key=KEYS["GEMINI"])
    p_desc = f"أنت {persona}. رد على مصعب بدقة."
    
    try:
        # تشغيل عائلة Gemini و Gemma
        if "gemini" in engine or "gemma" in engine:
            search = [types.Tool(google_search=types.GoogleSearch())] if use_search else None
            config = types.GenerateContentConfig(system_instruction=p_desc, tools=search)
            contents = [user_input]
            if image: contents.append(image)
            return client_gem.models.generate_content(model=engine, contents=contents, config=config).text
        
        # تشغيل محرك Ernie
        elif engine == "ernie-5.0":
            c = OpenAI(api_key=KEYS["ERNIE"], base_url="https://api.baidu.com/v1")
            r = c.chat.completions.create(model=engine, messages=[{"role": "user", "content": user_input}])
            return r.choices[0].message.content
            
        # تشغيل محرك Kimi
        elif engine == "kimi-latest":
            c = OpenAI(api_key=KEYS["KIMI"], base_url="https://api.moonshot.cn/v1")
            r = c.chat.completions.create(model="moonshot-v1-8k", messages=[{"role": "user", "content": user_input}])
            return r.choices[0].message.content
    except Exception as e: return f"⚠️ خطأ في {engine}: {str(e)}"

# --- 5. شريط التحكم والزر المفقود ---
if "messages" not in st.session_state: st.session_state.messages = load_history()

with st.sidebar:
    st.title("🛡️ مركز العمليات")
    
    # ميزة مسح السجل (إعادة الضبط المصنعي)
    if st.button("🗑️ مسح السجل وتصفير الذاكرة"):
        if os.path.exists("history.json"): os.remove("history.json")
        st.session_state.messages = []
        st.success("تم مسح السجل بنجاح!")
        st.rerun()
        
    st.divider()
    persona_choice = st.radio("👤 اختر الروح:", ["المدرس الذكي 👨‍🏫", "الخبير التقني 🛠️", "المساعد الشخصي 🤖"])
    engine_choice = st.selectbox("🎯 العقل النشط:", list(MODELS_GRID.keys()))
    web_on = st.toggle("🌐 بحث إنترنت", value=True)
    uploaded_file = st.file_uploader("📊 رفع (CSV/Images)", type=['csv', 'png', 'jpg'])

# --- 6. الرادار والعرض ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("أمرك يا مصعب...") or mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key='v19_mic'):
    u_txt = prompt if isinstance(prompt, str) else "🎤 [أمر صوتي]"
    st.session_state.messages.append({"role": "user", "content": u_txt})
    with st.chat_message("user"): st.markdown(u_txt)

    with st.chat_message("assistant"):
        img = Image.open(uploaded_file) if uploaded_file and uploaded_file.type.startswith('image') else None
        res = get_super_response(engine_choice, u_txt, persona_choice, img, web_on)
        st.markdown(res)
        
        # الرادار (كشف المسار المطلق)
        code_match = re.search(r'```python(.*?)```', res, flags=re.DOTALL)
        if code_match:
            with open("script.py", "w", encoding="utf-8") as f: f.write(code_match.group(1).strip())
            st.markdown(f'<div class="exec-box">📂 الرادار: {os.path.abspath("script.py")}</div>', unsafe_allow_html=True)

        st.session_state.messages.append({"role": "assistant", "content": res})
        save_history(st.session_state.messages)
