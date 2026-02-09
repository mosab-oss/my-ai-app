import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, time, pandas as pd
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 
from PIL import Image
import PyPDF2 # مكتبة معالجة الـ PDF

# --- 1. الإعدادات والسمات ---
st.set_page_config(page_title="منصة مصعب v16.39.0", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #000c18; border-left: 2px solid #00d4ff; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: monospace; }
    .status-badge { background-color: #1a1a1a; color: #ffcc00; border: 1px solid #ffcc00; padding: 2px 10px; border-radius: 20px; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# جلب المفاتيح السرية
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY")

# --- 2. محرك قراءة الملفات الذكي ---
def process_uploaded_file(uploaded_file):
    file_text = ""
    if uploaded_file.type == "application/pdf":
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            file_text += page.extract_text() + "\n"
        return f"\n[محتوى ملف PDF]:\n{file_text}"
    elif uploaded_file.type in ["text/csv", "application/vnd.ms-excel"]:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        return f"\n[بيانات الملف]:\n{df.head(10).to_string()}" # نرسل أول 10 أسطر للذكاء الاصطناعي
    return ""

# --- 3. محرك التنفيذ وحفظ الملفات ---
def run_execution_logic(text):
    clean_txt = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    file_match = re.search(r'SAVE_FILE:\s*([\w\.-]+)\s*\|\s*content=\{(.*?)\}', text, flags=re.DOTALL)
    exec_out = ""
    if file_match:
        fname, fcontent = file_match.group(1).strip(), file_match.group(2).strip()
        fcontent = re.sub(r'```python|```', '', fcontent).strip()
        try:
            with open(fname, 'w', encoding='utf-8') as f: f.write(fcontent)
            if fname.endswith('.py'):
                res = subprocess.run(['python3', fname], capture_output=True, text=True, timeout=10)
                exec_out = f"🖥️ ناتج تنفيذ كود {fname}:\n{res.stdout}\n{res.stderr}"
        except Exception as e: exec_out = f"❌ خطأ تنفيذ: {e}"
    return clean_txt, exec_out

# --- 4. دالة التوجيه الشاملة ---
def get_super_response(engine, user_input, persona, image=None, use_search=False, context_text=""):
    client = genai.Client(api_key=GEMINI_KEY)
    search_tool = [types.Tool(google_search=types.GoogleSearch())] if use_search else None
    
    # دمج سياق الملفات مع سؤال المستخدم
    full_prompt = f"{user_input}\n{context_text}" if context_text else user_input

    try:
        contents = [full_prompt]
        if image: contents.append(image)
        config = types.GenerateContentConfig(
            system_instruction=f"أنت {persona}. حلل البيانات المرفقة بدقة.",
            tools=search_tool
        )
        # تصحيح مسمى الموديل لضمان العمل
        target_model = engine if "gemini" in engine else "gemini-2.0-flash"
        r = client.models.generate_content(model=target_model, contents=contents, config=config)
        return r.text
    except Exception as e:
        return f"⚠️ عذراً مصعب، حدث خطأ: {str(e)}"

# --- 5. الواجهة الجانبية ---
with st.sidebar:
    st.title("🛡️ تحالف مصعب v16.39")
    audio = mic_recorder(start_prompt="🎤 تحدث", stop_prompt="إرسال", key='v39_mic')
    st.divider()
    
    engine_choice = st.selectbox(
        "🎯 العقل المفكر:", 
        ["gemini-2.0-flash", "gemini-2.0-pro-exp-02-05", "deepseek-r1"]
    )
    
    persona = st.selectbox("👤 الشخصية:", ["محلل بيانات خبير", "مساعد مبرمج", "مدرس لغات"])
    web_on = st.toggle("🌐 بحث إنترنت مباشر")
    uploaded_file = st.file_uploader("📂 ارفع (Image, PDF, CSV):", type=['jpg', 'png', 'pdf', 'csv', 'xlsx'])
    
    if st.button("🗑️ مسح السجل", type="primary"):
        st.session_state.messages = []; st.rerun()

# --- 6. العرض والتنفيذ ---
if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("تحدث مع نظامك...") or audio:
    txt = prompt if prompt else "🎤 [رسالة صوتية]"
    st.session_state.messages.append({"role": "user", "content": txt})
    with st.chat_message("user"): st.markdown(txt)

    with st.chat_message("assistant"):
        img_obj = None
        context_text = ""
        
        # معالجة الملفات المرفوعة
        if uploaded_file:
            if uploaded_file.type.startswith('image'):
                img_obj = Image.open(uploaded_file)
                st.markdown('<span class="status-badge">👁️ تم رصد صورة...</span>', unsafe_allow_html=True)
            else:
                with st.spinner("⏳ جاري قراءة الملف واستخراج البيانات..."):
                    context_text = process_uploaded_file(uploaded_file)
                    st.markdown('<span class="status-badge">📄 تم تحليل مستند المرفق</span>', unsafe_allow_html=True)

        with st.spinner("🧠 جاري التحليل والربط..."):
            raw_res = get_super_response(engine_choice, txt, persona, img_obj, web_on, context_text)
        
        clean_res, code_res = run_execution_logic(raw_res)
        st.markdown(clean_res)
        
        if code_res:
            st.markdown(f'<div class="exec-box">{code_res}</div>', unsafe_allow_html=True)
        
        # تحويل النص لصوت (اختياري)
        try:
            tts = gTTS(text=clean_res[:200], lang='ar')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass
        
        st.session_state.messages.append({"role": "assistant", "content": clean_res})
