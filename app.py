import streamlit as st
from google import genai
from google.genai import types
import io, re, os, subprocess, time, pandas as pd
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 
from PIL import Image
import PyPDF2
import binascii

# --- 1. إعدادات الهوية الفائقة ---
st.set_page_config(page_title="التحالف الفائق v17", layout="wide", page_icon="🔱")

# تصميم واجهة "التحالف" الاحترافية
st.markdown("""
    <style>
    .stApp { background-color: #050a10; color: #e0e0e0; }
    .main-header { font-size: 35px; color: #00d4ff; text-align: center; text-shadow: 0 0 10px #00d4ff; }
    .metric-card { background: rgba(0, 212, 255, 0.1); border: 1px solid #00d4ff; padding: 10px; border-radius: 10px; text-align: center; }
    .exec-log { background: #000; border-left: 5px solid #00ffcc; padding: 10px; font-family: 'Courier New', monospace; color: #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. وظائف المختبر والتحليل ---
def forensic_analysis(raw_input):
    """تحليل البيانات الثنائية (Hex) التي يرسلها مصعب"""
    if len(raw_input) > 100 and ('\\x' in raw_input or '0x' in raw_input):
        return "⚠️ تم رصد بيانات ثنائية! النظام جاهز لفك التشفير أو التحويل لملف."
    return None

def process_files(uploaded_file):
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = "\n".join([page.extract_text() for page in pdf_reader.pages])
        return f"[محتوى PDF]:\n{text}"
    elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel"]:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        return f"[بيانات الجدول]:\n{df.head(20).to_string()}"
    return ""

# --- 3. المحرك الذكي (Gemini 2.0) ---
def get_ai_response(prompt, context="", img=None, search=False):
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    tools = [types.Tool(google_search=types.GoogleSearch())] if search else None
    
    full_content = [f"سياق النظام: {context}\nطلب مصعب: {prompt}"]
    if img: full_content.append(img)
    
    config = types.GenerateContentConfig(
        system_instruction="أنت 'التحالف'، الذكاء الاصطناعي الخاص بمصعب. أنت خبير في البرمجة، الأمن السيبراني، وتحليل البيانات. نفذ الأوامر بدقة.",
        tools=tools
    )
    response = client.models.generate_content(model="gemini-2.0-flash", contents=full_content, config=config)
    return response.text

# --- 4. واجهة المستخدم الرسومية ---
st.markdown('<p class="main-header">🛡️ نظام التحالف الفائق v17.0.0</p>', unsafe_allow_html=True)

# صف العدادات (Metrics)
m1, m2, m3 = st.columns(3)
m1.markdown('<div class="metric-card">📡 حالة الاتصال: مستقر</div>', unsafe_allow_html=True)
m2.markdown('<div class="metric-card">🧠 العقل الحركي: Gemini 2.0</div>', unsafe_allow_html=True)
m3.markdown('<div class="metric-card">📂 المعالجة: شاملة (PDF/Hex)</div>', unsafe_allow_html=True)

st.divider()

# القائمة الجانبية
with st.sidebar:
    st.image("https://img.icons8.com/fluency/144/shield.png", width=100)
    st.title("إعدادات المهمة")
    web_search = st.toggle("تفعيل البحث العالمي (Live)")
    file = st.file_uploader("ارفع ملفاتك (PDF, Excel, Images)", type=['pdf', 'csv', 'xlsx', 'png', 'jpg'])
    if st.button("🔴 تصفير الذاكرة"):
        st.session_state.chat_history = []
        st.rerun()

# سجل الدردشة
if "chat_history" not in st.session_state: st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# إدخال المستخدم
if user_input := st.chat_input("أمرك مطاع يا مصعب..."):
    # تحليل فوري للبيانات الثنائية
    forensic_msg = forensic_analysis(user_input)
    
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"): st.markdown(user_input)

    with st.chat_message("assistant"):
        file_context = ""
        img_obj = None
        
        if file:
            if file.type.startswith('image'): img_obj = Image.open(file)
            else: file_context = process_files(file)
        
        if forensic_msg: st.info(forensic_msg)
        
        with st.spinner("🌀 التحالف يفكر..."):
            raw_res = get_ai_response(user_input, file_context, img_obj, web_search)
            
        # معالجة الأكواد (SAVE_FILE)
        clean_text = re.sub(r'<think>.*?</think>', '', raw_res, flags=re.DOTALL)
        st.markdown(clean_text)
        
        # تنفيذ كود تلقائي إذا وجد
        if "```python" in raw_res:
            st.markdown('<p style="color:#00ffcc;">💻 تم رصد كود برمجي جاهز للتنفيذ...</p>', unsafe_allow_html=True)

        st.session_state.chat_history.append({"role": "assistant", "content": clean_text})
