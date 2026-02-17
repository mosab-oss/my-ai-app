import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, requests
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الواجهة (مستوحاة من v16.12 المستقر) ---
st.set_page_config(page_title="منصة مصعب v16.29.0", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #000c18; direction: rtl; border-left: 2px solid #00d4ff; }
    .teacher-box { background-color: #002b36; color: #00ffcc; padding: 15px; border-radius: 10px; border-right: 5px solid #00d4ff; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# جلب المفاتيح
API_KEY_GEMINI = st.secrets.get("GEMINI_API_KEY")
API_KEY_KIMI = st.secrets.get("KIMI_API_KEY")
API_KEY_ERNIE = st.secrets.get("ERNIE_API_KEY")

# --- 2. محرك التنفيذ الصامت (ميزة v16.12) ---
def execute_logic(text):
    display_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    file_pattern = r'SAVE_FILE:\s*([\w\.-]+)\s*\|\s*content=\{(.*?)\}'
    match = re.search(file_pattern, text, flags=re.DOTALL)
    exec_output = ""
    if match:
        fname, fcontent = match.group(1).strip(), match.group(2).strip()
        fcontent = re.sub(r'```python|```', '', fcontent).strip()
        try:
            with open(fname, 'w', encoding='utf-8') as f: f.write(fcontent)
            if fname.endswith('.py'):
                res = subprocess.run(['python3', fname], capture_output=True, text=True, timeout=10)
                exec_output = f"🖥️ ناتج التنفيذ:\n{res.stdout}\n{res.stderr}"
        except Exception as e: exec_output = f"❌ خطأ: {e}"
    return display_text, exec_output

# --- 3. دالة التوجيه الشاملة (v16.28.5 المدمجة) ---
def universal_router(engine, user_input, persona_type):
    teacher_instr = "أنت مدرس لغة خبير. مهمتك: الترجمة، تصحيح القواعد، وشرح المفردات بأسلوب تعليمي."
    default_instr = f"أنت {persona_type}. أجب باللغة العربية بوضوح."
    current_instr = teacher_instr if engine == "مدرس اللغة المتخصص" else default_instr

    try:
        # مسار Gemini & Gemma & Teacher
        if any(x in engine for x in ["gemini", "gemma"]) or engine == "مدرس اللغة المتخصص":
            target_model = "gemini-2.5-flash" if engine == "مدرس اللغة المتخصص" else engine
            client = genai.Client(api_key=API_KEY_GEMINI)
            res = client.models.generate_content(
                model=target_model, contents=user_input, 
                config=types.GenerateContentConfig(system_instruction=current_instr)
            )
            return res.text

        # مسار DeepSeek (محلي)
        elif "deepseek" in engine:
            client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
            res = client.chat.completions.create(
                model="deepseek-r1", messages=[{"role": "system", "content": current_instr}, {"role": "user", "content": user_input}]
            )
            return res.choices[0].message.content

        # مسار Kimi
        elif "kimi" in engine:
            client = OpenAI(base_url="https://api.moonshot.cn/v1", api_key=API_KEY_KIMI)
            res = client.chat.completions.create(
                model="moonshot-v1-8k", messages=[{"role": "system", "content": current_instr}, {"role": "user", "content": user_input}]
            )
            return res.choices[0].message.content

        # مسار ERNIE
        elif "ernie" in engine:
            client = OpenAI(base_url="https://api.baidu.com/v1", api_key=API_KEY_ERNIE)
            res = client.chat.completions.create(
                model="ernie-5.0", messages=[{"role": "system", "content": current_instr}, {"role": "user", "content": user_input}]
            )
            return res.choices[0].message.content

    except Exception as e:
        return f"❌ خطأ في بوابة {engine}: {str(e)}"
    return "❌ المحرك غير متاح."

# --- 4. القائمة الجانبية (v16.12 المحدثة) ---
with st.sidebar:
    st.title("🛡️ منصة مصعب الموحدة")
    audio_record = mic_recorder(start_prompt="🎤 المغرفون", stop_prompt="إرسال", key='v29_mic')
    st.divider()
    
    engine_choice = st.selectbox(
        "🎯 المحرك النشط:", 
        ["مدرس اللغة المتخصص", "gemini-2.5-flash", "gemini-3-pro-preview", "gemma-3-27b", "deepseek-r1", "kimi-latest", "ernie-5.0"]
    )
    
    persona = st.selectbox("👤 الشخصية:", ["المعرفون", "مساعد مبرمج", "وكيل تنفيذ"])
    
    if st.button("🗑️ مسح المحادثة", type="primary"):
        st.session_state.messages = []
        st.rerun()

# --- 5. منطق الدردشة والنطق ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("تحدث مع النظام...") or audio_record:
    user_txt = prompt if prompt else "🎤 [أمر صوتي]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        if engine_choice == "مدرس اللغة المتخصص":
            st.markdown('<div class="teacher-box">🎓 المدرس النشط الآن...</div>', unsafe_allow_html=True)

        reply = universal_router(engine_choice, user_txt, persona)
        clean_txt, exec_res = execute_logic(reply)
        
        if clean_txt:
            st.markdown(clean_txt)
            if exec_res: st.markdown(f'<div class="exec-box">{exec_res}</div>', unsafe_allow_html=True)
            
            # النطق الصوتي (ميزة v16.12)
            try:
                tts = gTTS(text=clean_txt[:250], lang='ar')
                fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)
            except: pass
        
        st.session_state.messages.append({"role": "assistant", "content": clean_txt})
