import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, time
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 
from PIL import Image

# --- 1. الإعدادات والسمات ---
st.set_page_config(page_title="تحالف مصعب v16.36", layout="wide", page_icon="👁️")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #000c18; border-left: 2px solid #00d4ff; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: monospace; }
    .vision-badge { background-color: #004411; color: #00ff88; padding: 5px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

KEYS = {
    "GEMINI": st.secrets.get("GEMINI_API_KEY"),
    "KIMI": st.secrets.get("KIMI_API_KEY"),
    "ERNIE": st.secrets.get("ERNIE_API_KEY")
}

# --- 2. محرك التنفيذ الصامت (v16.12) ---
def run_code_logic(text):
    clean_display = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    file_pattern = r'SAVE_FILE:\s*([\w\.-]+)\s*\|\s*content=\{(.*?)\}'
    match = re.search(file_pattern, text, flags=re.DOTALL)
    output = ""
    if match:
        name, content = match.group(1).strip(), match.group(2).strip()
        content = re.sub(r'```python|```', '', content).strip()
        try:
            with open(name, 'w', encoding='utf-8') as f: f.write(content)
            if name.endswith('.py'):
                res = subprocess.run(['python3', name], capture_output=True, text=True, timeout=10)
                output = f"🖥️ ناتج تنفيذ {name}:\n{res.stdout}\n{res.stderr}"
        except Exception as e: output = f"❌ خطأ برمي: {e}"
    return clean_display, output

# --- 3. دالة التوجيه العالمي مع دعم الرؤية (Vision Support) ---
def fetch_response(engine, user_input, persona_type, image_data=None):
    instr = f"أنت {persona_type}. حلل ما يطلبه المستخدم بدقة."
    gemini_client = genai.Client(api_key=KEYS["GEMINI"])

    # نظام الطوارئ والتبديل لـ Gemini
    def try_gemini_fallback(msg, img=None):
        try:
            content_list = [msg]
            if img: content_list.append(img)
            r = gemini_client.models.generate_content(model="gemini-2.0-flash", contents=content_list)
            return r.text
        except Exception as err:
            if "429" in str(err):
                bar = st.empty()
                for s in range(25, 0, -1):
                    bar.warning(f"⚠️ زحام! إعادة المحاولة خلال {s} ثانية...")
                    time.sleep(1)
                bar.empty()
                return gemini_client.models.generate_content(model="gemini-2.0-flash", contents=content_list).text
            return f"❌ خطأ: {err}"

    # إذا كانت هناك صورة، نستخدم Gemini حصراً لأنها الأقوى في الرؤية
    if image_data:
        return try_gemini_fallback(user_input, image_data)

    try:
        # المسارات العادية للمحركات الأخرى (Kimi, Ernie, DeepSeek)
        if "ernie" in engine and KEYS["ERNIE"]:
            c = OpenAI(api_key=KEYS["ERNIE"], base_url="https://api.baidu.com/v1")
            res = c.chat.completions.create(model="ernie-5.0", messages=[{"role": "user", "content": user_input}])
            return res.choices[0].message.content
        
        elif "deepseek" in engine:
            try:
                c = OpenAI(api_key="lm-studio", base_url="http://localhost:1234/v1")
                res = c.chat.completions.create(model="deepseek-r1", messages=[{"role": "user", "content": user_input}], timeout=5)
                return res.choices[0].message.content
            except: return try_gemini_fallback(user_input)

        return try_gemini_fallback(user_input)
    except:
        return try_gemini_fallback(user_input)

# --- 4. الواجهة الجانبية (v16.36) ---
with st.sidebar:
    st.title("🛡️ منصة مصعب الشاملة")
    audio = mic_recorder(start_prompt="🎤 تحدث", stop_prompt="توقف", key='v36_mic')
    st.divider()
    choice = st.selectbox("🎯 المحرك:", ["gemini-2.0-flash", "ernie-5.0", "kimi-latest", "deepseek-r1"])
    role = st.selectbox("👤 الشخصية:", ["مساعد مبرمج", "المعرفون", "محلل صور ذكي"])
    
    # ميزة الرؤية الجديدة
    uploaded_img = st.file_uploader("🖼️ ارفع صورة لتحليلها:", type=['jpg', 'png', 'jpeg'])
    if uploaded_img:
        st.image(uploaded_img, caption="الصورة المرفوعة", use_container_width=True)

    if st.button("🗑️ مسح السجل"):
        st.session_state.messages = []; st.rerun()

# --- 5. العرض والمعالجة ---
if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("اسأل أو ارفع صورة لنحللها...") or audio:
    txt = prompt if prompt else "🎤 [رسالة صوتية]"
    st.session_state.messages.append({"role": "user", "content": txt})
    with st.chat_message("user"): st.markdown(txt)

    with st.chat_message("assistant"):
        # تحضير الصورة إذا وجدت
        img_obj = None
        if uploaded_img:
            img_obj = Image.open(uploaded_img)
            st.markdown('<span class="vision-badge">👁️ جاري تحليل الصورة...</span>', unsafe_allow_html=True)

        raw = fetch_response(choice, txt, role, img_obj)
        clean, code_out = run_code_logic(raw)
        
        st.markdown(clean)
        if code_out: st.markdown(f'<div class="exec-box">{code_out}</div>', unsafe_allow_html=True)
        
        try:
            tts = gTTS(text=clean[:250], lang='ar')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
        st.session_state.messages.append({"role": "assistant", "content": clean})
