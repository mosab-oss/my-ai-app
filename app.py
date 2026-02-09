import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, time, json, pandas as pd
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 
from PIL import Image

# --- 1. إدارة الذاكرة والسجل ---
def load_history():
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f: return json.load(f)
    return []

def save_history(messages):
    with open("history.json", "w", encoding="utf-8") as f: 
        json.dump(messages, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="تحالف مصعب v16.46.15 - النسخة المثبتة", layout="wide", page_icon="🛡️")

# --- 2. الواجهة والجماليات ---
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #000c18; border-left: 2px solid #00d4ff; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: monospace; }
    .stButton>button { width: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

KEYS = {
    "GEMINI": st.secrets.get("GEMINI_API_KEY"),
    "ERNIE": st.secrets.get("ERNIE_API_KEY"),
    "KIMI": st.secrets.get("KIMI_API_KEY")
}

# --- 3. العقل الموجه (قائمة العقول السبعة المثبتة) ---
MODELS_GRID = [
    "gemini-2.5-flash", 
    "gemini-2.0-flash",
    "gemini-3-pro-preview", 
    "gemma-3-27b", 
    "deepseek-r1", 
    "ernie-5.0", 
    "kimi-latest"
]

def get_super_response(engine, user_input, persona_type, image=None, use_search=False):
    client_gem = genai.Client(api_key=KEYS["GEMINI"])
    persona_desc = f"أنت {persona_type}. رد على مصعب بدقة واحترافية."
    
    try:
        # عائلة جوجل
        if "gemini" in engine or "gemma" in engine:
            search_tool = [types.Tool(google_search=types.GoogleSearch())] if use_search else None
            config = types.GenerateContentConfig(system_instruction=persona_desc, tools=search_tool)
            contents = [user_input]
            if image: contents.append(image)
            return client_gem.models.generate_content(model=engine, contents=contents, config=config).text
        
        # محرك Ernie 5.0
        elif engine == "ernie-5.0":
            c = OpenAI(api_key=KEYS["ERNIE"], base_url="https://api.baidu.com/v1")
            r = c.chat.completions.create(model="ernie-5.0", messages=[{"role": "system", "content": persona_desc}, {"role": "user", "content": user_input}])
            return r.choices[0].message.content
            
        # محرك Kimi
        elif engine == "kimi-latest":
            c = OpenAI(api_key=KEYS["KIMI"], base_url="https://api.moonshot.cn/v1")
            r = c.chat.completions.create(model="moonshot-v1-8k", messages=[{"role": "system", "content": persona_desc}, {"role": "user", "content": user_input}])
            return r.choices[0].message.content

        # محرك DeepSeek R1 (محلي أو عبر API)
        elif engine == "deepseek-r1":
            c = OpenAI(api_key="sk-xxx", base_url="https://api.deepseek.com") # أو رابط LM Studio
            r = c.chat.completions.create(model="deepseek-reasoner", messages=[{"role": "user", "content": user_input}])
            return r.choices[0].message.content
            
    except Exception as e: return f"❌ خطأ في المحرك {engine}: {str(e)}"

# --- 4. الرادار v16.46.15 ---
def run_and_autofix(text, engine, persona):
    clean_txt = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    code_match = re.search(r'```python(.*?)```', text, flags=re.DOTALL)
    exec_out = ""
    if code_match:
        code = code_match.group(1).strip()
        fname = "auto_script.py"
        full_path = os.path.abspath(fname)
        with open(fname, "w", encoding="utf-8") as f: f.write(code)
        res = subprocess.run(['python3', fname], capture_output=True, text=True, timeout=30)
        exec_out = f"📂 **المجلد:** `{os.getcwd()}`\n📜 **الرادار:** `{full_path}`\n\n"
        exec_out += f"🖥️ **الناتج:**\n{res.stdout if not res.stderr else res.stderr}"
    return clean_txt, exec_out

# --- 5. شريط التحكم والجانبية ---
if "messages" not in st.session_state: st.session_state.messages = load_history()

with st.sidebar:
    st.title("🛡️ منصة مصعب المثبتة")
    audio_mic = mic_recorder(start_prompt="🎤 تحدث", stop_prompt="⏹️", key='v15_mic')
    
    # ميزة مسح السجل (المثبتة)
    if st.button("🧹 مسح سجل المحادثات", type="primary"):
        st.session_state.messages = []
        save_history([])
        st.rerun()

    st.divider()
    persona = st.radio("👤 الشخصية النشطة:", ["المدرس الذكي 👨‍🏫", "الخبير التقني 🛠️", "المساعد الشخصي 🤖"])
    
    # قائمة العقول المثبتة (بدون نواقص)
    engine_choice = st.selectbox("🎯 اختر العقل:", MODELS_GRID)
    
    st.divider()
    uploaded_file = st.file_uploader("📊 رفع بيانات أو صور", type=['csv', 'xlsx', 'jpg', 'png'])
    web_on = st.toggle("🌐 تفعيل البحث العالمي", value=True)

# --- 6. معالجة الحوار ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("اطلب أي شيء من فريقك الذكي...") or audio_mic:
    txt = prompt if isinstance(prompt, str) else "🎤 [أمر صوتي مستلم]"
    st.session_state.messages.append({"role": "user", "content": txt})
    with st.chat_message("user"): st.markdown(txt)

    with st.chat_message("assistant"):
        img_obj = Image.open(uploaded_file) if uploaded_file and uploaded_file.type.startswith('image') else None
        raw_res = get_super_response(engine_choice, txt, persona, img_obj, web_on)
        clean_res, code_res = run_and_autofix(raw_res, engine_choice, persona)
        
        st.markdown(clean_res)
        if code_res: st.markdown(f'<div class="exec-box">{code_res}</div>', unsafe_allow_html=True)
        
        st.session_state.messages.append({"role": "assistant", "content": clean_res})
        save_history(st.session_state.messages)
        
        try:
            tts = gTTS(text=clean_res[:150], lang='ar')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
