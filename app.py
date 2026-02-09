import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import io
from PIL import Image
import PyPDF2

# --- 1. الإعدادات الأساسية للنسخة v16.12.0 ---
st.set_page_config(page_title="التحالف v16.12.0", layout="wide", page_icon="⚡")

# تصميم الواجهة الاحترافي والهادئ
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .status-box { padding: 10px; border-radius: 5px; border-left: 5px solid #238636; background: #161b22; }
    .main-title { color: #58a6ff; text-align: center; font-size: 30px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. وظائف المعالجة المركزية ---
def process_document(file):
    """معالجة ملفات PDF و Excel"""
    if file.type == "application/pdf":
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() for page in reader.pages])
    elif file.name.endswith(('.csv', '.xlsx')):
        df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
        return df.to_string()
    return ""

# --- 3. محرك Gemini v16.12.0 ---
def call_gemini(prompt, file_data="", image=None):
    # تأكد من وضع الـ API KEY الخاص بك في Secrets
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    contents = [f"سياق الملفات: {file_data}\n\nسؤال المستخدم: {prompt}"]
    if image:
        contents.append(image)
        
    response = client.models.generate_content(
        model="gemini-2.0-flash", # المحرك الافتراضي للنسخة
        contents=contents
    )
    return response.text

# --- 4. واجهة المستخدم ---
st.markdown('<p class="main-title">🛡️ نظام التحالف - الإصدار v16.12.0</p>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ لوحة التحكم")
    st.info("الحالة: مستقر ✅")
    uploaded_file = st.file_uploader("إرفاق مستند أو صورة", type=['pdf', 'csv', 'xlsx', 'png', 'jpg'])
    st.divider()
    if st.button("🗑️ مسح الذاكرة"):
        st.session_state.chat_history = []
        st.rerun()

# سجل الدردشة
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# منطقة الإدخال
if user_input := st.chat_input("تحدث مع التحالف..."):
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        context = ""
        img_obj = None
        
        if uploaded_file:
            if uploaded_file.type.startswith('image'):
                img_obj = Image.open(uploaded_file)
            else:
                context = process_document(uploaded_file)
        
        with st.spinner("جاري المعالجة..."):
            answer = call_gemini(user_input, context, img_obj)
            st.markdown(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
