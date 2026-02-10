import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import io
from PIL import Image
import PyPDF2

# --- 1. إعدادات الصفحة والواجهة ---
st.set_page_config(page_title="التحالف v16.12.0", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .status-box { padding: 10px; border-radius: 5px; border-left: 5px solid #238636; background: #161b22; }
    .main-title { color: #58a6ff; text-align: center; font-size: 30px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. وظائف معالجة الملفات ---
def process_document(file):
    try:
        if file.type == "application/pdf":
            reader = PyPDF2.PdfReader(file)
            return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif file.name.endswith(('.csv', '.xlsx')):
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            return df.head(100).to_string() # قراءة أول 100 سطر للتحليل
    except Exception as e:
        return f"خطأ في قراءة الملف: {e}"
    return ""

# --- 3. الاتصال بمحرك Gemini ---
def call_gemini(prompt, file_data="", image=None):
    # سيستخدم النظام المفتاح المخزن في Streamlit Secrets
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    full_prompt = f"سياق البيانات المرفقة:\n{file_data}\n\nطلب المستخدم: {prompt}"
    contents = [full_prompt]
    
    if image:
        contents.append(image)
        
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents
    )
    return response.text

# --- 4. تصميم واجهة المستخدم (كما في الصورة) ---
st.markdown('<p class="main-title">🛡️ v16.12.0 نظام التحالف - الإصدار</p>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ لوحة التحكم")
    st.success("الحالة: مستقر ✅")
    
    uploaded_file = st.file_uploader("إرفاق مستند أو صورة", type=['pdf', 'csv', 'xlsx', 'png', 'jpg'])
    
    st.divider()
    if st.button("🗑️ مسح الذاكرة"):
        st.session_state.chat_history = []
        st.rerun()

# تهيئة سجل المحادثة
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# عرض المحادثة
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# منطقة إدخال الأوامر
if user_input := st.chat_input("تحدث مع التحالف..."):
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        file_context = ""
        img_obj = None
        
        if uploaded_file:
            if uploaded_file.type.startswith('image'):
                img_obj = Image.open(uploaded_file)
            else:
                with st.status("🔍 جاري تحليل المستند..."):
                    file_context = process_document(uploaded_file)
        
        with st.spinner("🌀 التحالف يحلل الطلب..."):
            try:
                answer = call_gemini(user_input, file_context, img_obj)
                st.markdown(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"حدث خطأ في الاتصال بالمحرك: {e}")
