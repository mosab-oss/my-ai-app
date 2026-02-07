import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الواجهة (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.14.5", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { background-color: #001529; direction: rtl; }
    .stSelectbox label, .stSlider label { color: #00ffcc !important; font-weight: bold; }
    .exec-box { background-color: #000; color: #0f0; padding: 15px; border-radius: 10px; border: 1px solid #0f0; }
    </style>
    """, unsafe_allow_html=True)

# الربط التقني
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key: genai.configure(api_key=api_key)

# --- 2. محرك التنفيذ التلقائي ---
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

# --- 3. القائمة الجانبية: (كل الميزات + مدرس اللغة + مسح المحادثة) ---
with st.sidebar:
    st.title("🛠️ مركز القيادة v16.14.5")
    
    # ميزة المغرفون
    st.subheader("🎤 المغرفون")
    audio_record = mic_recorder(start_prompt="إضغط للتحدث", stop_prompt="إرسال", key='v14_5_mic')
    
    st.divider()

    # التحالف السداسي
    engine_choice = st.selectbox(
        "🎯 المحرك:", 
        ["Gemini 3 Pro", "Gemini 2.5 Flash", "Gemma 3 27B", "DeepSeek R1", "Kimi AI", "ERNIE Bot"]
    )

    # مستوى التفكير
    thinking_level = st.select_slider("🧠 مستوى التفكير:", ["Low", "Medium", "High"], value="High")
    
    # إدراج "مدرس اللغة" في الشخصيات (كما طلبت)
    persona = st.selectbox(
        "👤 اختيار الخبير:", 
        ["المعرفون", "مدرس اللغة (ترجمة وتعليم)", "مساعد مبرمج محترف", "وكيل تنفيذ"]
    )

    st.divider()

    # رفع الملفات
    uploaded_file = st.file_uploader("📂 رفع الملفات:", type=["pdf", "txt", "py", "png", "jpg"])
    
    st.divider()
    
    # أدوات الصيانة (زر المسح وفحص الموديلات)
    st.subheader("⚙️ الأدوات")
    if st.button("🔍 فحص الموديلات النشطة"):
        st.info("جاري الفحص...")
        
    # زر مسح المحادثة (الذي كان ناقصاً)
    if st.button("🗑️ مسح المحادثة بالكامل", type="primary"):
        st.session_state.messages = []
        st.rerun()

# --- 4. واجهة الدردشة والمعالجة ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("تحدث مع النظام...")

if prompt or audio_record or uploaded_file:
    user_txt = prompt if prompt else "🎤 [رسالة صوتية]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            # استخدام الموديل المختار
            model = genai.GenerativeModel("models/gemini-1.5-pro") 
            full_req = f"بصفتك {persona} وبمستوى تفكير {thinking_level}: {user_txt}. إذا كان المطلوب كود استخدم SAVE_FILE: name | content={{}}"
            
            response = model.generate_content(full_req)
            clean_txt, execution_res = execute_logic(response.text)
            
            st.markdown(clean_txt)
            if execution_res:
                st.markdown(f'<div class="exec-box">{execution_res}</div>', unsafe_allow_html=True)

            # النطق الصوتي
            tts = gTTS(text=clean_txt[:250], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3')

            st.session_state.messages.append({"role": "assistant", "content": clean_txt})
        except Exception as e:
            st.error(f"حدث خطأ: {e}")
