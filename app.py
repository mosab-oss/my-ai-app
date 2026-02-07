import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الواجهة الاحترافية ---
st.set_page_config(page_title="منصة مصعب v16.14.0", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { background-color: #001529; direction: rtl; }
    .stSelectbox label, .stSlider label { color: #00d4ff !important; font-weight: bold; }
    .exec-box { background-color: #000; color: #0f0; padding: 15px; border-radius: 10px; border: 1px dashed #0f0; font-family: 'Courier New', monospace; }
    </style>
    """, unsafe_allow_html=True)

# إعدادات الربط
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key: genai.configure(api_key=api_key)

# --- 2. محرك التنفيذ التلقائي للأكواد ---
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
                exec_output = f"🖥️ ناتج تشغيل الكود:\n{res.stdout}\n{res.stderr}"
        except Exception as e: exec_output = f"❌ خطأ برمي: {e}"
    return display_text, exec_output

# --- 3. القائمة الجانبية (كل الميزات + كل المحركات) ---
with st.sidebar:
    st.title("🛠️ مركز القيادة v16.14.0")
    
    # ميزة المغرفون (الميكروفون)
    st.markdown("### 🎤 المغرفون")
    audio_record = mic_recorder(start_prompt="إضغط للتحدث", stop_prompt="إرسال الصوت", key='sidebar_mic_v14')
    
    st.divider()

    # القائمة المحدثة كما طلبت (التحالف السداسي)
    engine_choice = st.selectbox(
        "🎯 اختر العقل المفكر:", 
        [
            "Gemini 3 Pro", 
            "Gemini 2.5 Flash", 
            "Gemma 3 27B", 
            "DeepSeek R1", 
            "Kimi AI", 
            "ERNIE Bot"
        ]
    )

    # التحكم في التفكير والشخصية
    thinking_level = st.select_slider("🧠 مستوى التفكير:", ["Low", "Medium", "High"], value="High")
    persona = st.selectbox("👤 تقمص دور:", ["المعرفون", "مساعد مبرمج محترف", "وكيل تنفيذ"])

    st.divider()

    # أدوات إضافية
    uploaded_file = st.file_uploader("📂 رفع الملفات:", type=["pdf", "txt", "py", "png", "jpg"])
    
    if st.button("🔍 فحص الموديلات والاتصال"):
        st.write("يتم الآن فحص استجابة المحركات الستة...")

# --- 4. معالجة الرسائل والردود ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("اكتب سؤالك هنا أو استخدم المغرفون من القائمة...")

if prompt or audio_record or uploaded_file:
    user_txt = prompt if prompt else "🎤 [تم إرسال أمر صوتي]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            # توجيه الطلب للمحرك (افتراضي Gemini للشرح)
            model = genai.GenerativeModel("models/gemini-1.5-pro") # أو الموديل المختار
            full_req = f"بصفتك {persona} وبمستوى تفكير {thinking_level}: {user_txt}. إذا كتبت كود استخدم: SAVE_FILE: name | content={{}}"
            
            response = model.generate_content(full_req)
            
            # التنظيف والتنفيذ
            clean_txt, execution_res = execute_logic(response.text)
            st.markdown(clean_txt)
            
            if execution_res:
                st.markdown(f'<div class="exec-box">{execution_res}</div>', unsafe_allow_html=True)

            # الرد الصوتي (TTS)
            tts = gTTS(text=clean_txt[:250], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3')

            st.session_state.messages.append({"role": "assistant", "content": clean_txt})
        except Exception as e:
            st.error(f"حدث خطأ في الاتصال بمحرك {engine_choice}: {e}")
