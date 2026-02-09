import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, time, json, pandas as pd
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder, speech_to_text
from PIL import Image

# --- 1. إدارة الذاكرة والسجل السيادي ---
def load_history():
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def save_history(messages):
    with open("history.json", "w", encoding="utf-8") as f: 
        json.dump(messages, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="تحالف مصعب v16.46.22 - النسخة الشاملة", layout="wide", page_icon="🛡️")

# --- 2. التصميم الاحترافي ---
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #000c18; border-left: 2px solid #00d4ff; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: monospace; }
    .mic-box { border: 1px solid #00d4ff; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    .stButton>button { width: 100%; background-color: #d32f2f; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. مصفوفة العقول السبعة (كاملة وبدون نواقص) ---
MODELS_GRID = {
    "Gemini 3 Flash (الأحدث)": "gemini-3-flash",
    "Gemini 2.5 Flash": "gemini-2.5-flash", 
    "Gemini 2.0 Flash": "gemini-2.0-flash-exp",
    "Gemini 1.5 Pro": "gemini-1.5-pro",
    "Gemma 3 27B": "gemma-3-27b",
    "DeepSeek R1": "deepseek-reasoner",
    "Ernie 5.0 (الصين)": "ernie-5.0",
    "Kimi Latest": "moonshot-v1-8k"
}

KEYS = {
    "GEMINI": st.secrets.get("GEMINI_API_KEY"),
    "ERNIE": st.secrets.get("ERNIE_API_KEY"),
    "KIMI": st.secrets.get("KIMI_API_KEY")
}

# --- 4. محرك الاستجابة المتعدد ---
def get_super_response(engine_label, user_input, persona_type, image=None):
    engine_id = MODELS_GRID.get(engine_label)
    try:
        # عائلة جوجل (Gemini & Gemma)
        if "Gemini" in engine_label or "Gemma" in engine_label:
            client = genai.Client(api_key=KEYS["GEMINI"])
            config = types.GenerateContentConfig(system_instruction=f"أنت {persona_type}")
            contents = [user_input]
            if image: contents.append(image)
            response = client.models.generate_content(model=engine_id, contents=contents, config=config)
            return response.text
        
        # محرك Ernie
        elif "Ernie" in engine_label:
            c = OpenAI(api_key=KEYS["ERNIE"], base_url="https://api.baidu.com/v1")
            r = c.chat.completions.create(model="ernie-5.0", messages=[{"role": "user", "content": user_input}])
            return r.choices[0].message.content

        # محرك Kimi
        elif "Kimi" in engine_label:
            c = OpenAI(api_key=KEYS["KIMI"], base_url="https://api.moonshot.cn/v1")
            r = c.chat.completions.create(model="moonshot-v1-8k", messages=[{"role": "user", "content": user_input}])
            return r.choices[0].message.content
            
    except Exception as e:
        return f"⚠️ خطأ في {engine_label}: {str(e)}"

# --- 5. شريط التحكم الجانبي ---
if "messages" not in st.session_state: st.session_state.messages = load_history()

with st.sidebar:
    st.title("🎤 مركز العمليات v22")
    
    # ميزة الميكروفون
    st.markdown('<div class="mic-box">', unsafe_allow_html=True)
    audio_input = speech_to_text(language='ar', start_prompt="🎙️ تحدث الآن", stop_prompt="⏹️ توقف", key='mic_v22')
    st.markdown('</div>', unsafe_allow_html=True)

    # ميزة مسح السجل (المثبتة)
    if st.button("🗑️ مسح السجل وتصفير الذاكرة"):
        st.session_state.messages = []
        if os.path.exists("history.json"): os.remove("history.json")
        st.success("تم التصفير!")
        st.rerun()

    st.divider()
    persona = st.radio("👤 الشخصية النشطة:", ["المدرس الذكي 👨‍🏫", "الخبير التقني 🛠️", "المساعد الشخصي 🤖"])
    engine_choice = st.selectbox("🎯 اختر العقل:", list(MODELS_GRID.keys()))
    uploaded_file = st.file_uploader("📊 رفع (CSV/Images)", type=['csv', 'png', 'jpg'])

# --- 6. معالجة الحوار والرادار ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# دمج مدخلات الميكروفون مع الكتابة
chat_input = st.chat_input("اكتب أمرك هنا يا مصعب...")
final_prompt = audio_input if audio_input else chat_input

if final_prompt:
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"): st.markdown(final_prompt)

    with st.chat_message("assistant"):
        img_obj = Image.open(uploaded_file) if uploaded_file and uploaded_file.type.startswith('image') else None
        response = get_super_response(engine_choice, final_prompt, persona, img_obj)
        st.markdown(response)
        
        # الرادار (كشف المسار المطلق للأكواد)
        code_match = re.search(r'```python(.*?)```', response, flags=re.DOTALL)
        if code_match:
            with open("radar_script.py", "w", encoding="utf-8") as f: f.write(code_match.group(1).strip())
            st.markdown(f'<div class="exec-box">📂 الرادار: {os.path.abspath("radar_script.py")}</div>', unsafe_allow_html=True)

        # النطق الآلي للرد
        try:
            tts = gTTS(text=response[:150], lang='ar')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass

        st.session_state.messages.append({"role": "assistant", "content": response})
        save_history(st.session_state.messages)
