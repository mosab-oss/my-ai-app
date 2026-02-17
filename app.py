
import streamlit as st
import os
import time
import io
import base64
from google import genai
from google.genai import types
from openai import OpenAI
from PIL import Image
import pdfplumber  # لإضافة ميزة قراءة الـ PDF

# --- [1] الإعدادات الأساسية ومجلس الخبراء ---
model_map = {
    "Gemini 2.0 Flash": "gemini-2.0-flash-exp",
    "Gemini 1.5 Pro": "gemini-1.5-pro",
    "Gemini 1.5 Flash": "gemini-1.5-flash"
}

expert_map = {
    "🌍 خبير عام": "أنت مستشار عام ذكي، تجيب بدقة ووضوح. تذكر سياق المحادثة السابق دائماً.",
    "💻 خبير تقني": "أنت خبير برمجيات، ركز على الكود النظيف واكتشاف الثغرات وتطوير الحلول.",
    "📈 محلل أسواق": "أنت خبير مالي، استخدم البحث الحي لتحليل الأسواق والعملات بدقة.",
    "⚖️ مستشار قانوني": "أنت خبير قانوني، مراجع للعقود والامتثال والوثائق الرسمية."
}

# دالة استخراج النص من PDF
def extract_pdf_text(uploaded_file):
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

if "request_count" not in st.session_state: st.session_state.request_count = 0
if "messages" not in st.session_state: st.session_state.messages = []

# --- [2] المحرك التنفيذي المطور (مع الذاكرة) ---
def run_engine(prompt_data, is_voice=False, image_data=None, pdf_text=None):
    target_model = model_map.get(selected_model, "gemini-1.5-flash")
    expert_instruction = expert_map.get(selected_expert, "خبير عام")

    try:
        if provider == "Google Gemini":
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            
            # تكوين الذاكرة (إرسال تاريخ المحادثة)
            history = []
            for msg in st.session_state.messages[-10:]: # آخر 10 رسائل للحفاظ على الأداء
                role = "user" if msg["role"] == "user" else "model"
                history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

            config = types.GenerateContentConfig(
                system_instruction=expert_instruction,
                tools=[types.Tool(google_search=types.GoogleSearch())] if live_search else None,
                temperature=0.7
            )

            # تجهيز المدخلات (نص + صورة + PDF)
            content_parts = []
            if pdf_text:
                content_parts.append(f"محتوى ملف الـ PDF المرفق:\n{pdf_text}\n\nالسؤال:")
            
            if is_voice:
                content_parts.append(types.Part.from_bytes(data=prompt_data['bytes'], mime_type="audio/wav"))
            else:
                content_parts.append(prompt_data)

            if image_data:
                content_parts.append(Image.open(image_data))

            # إنشاء جلسة شات تدعم الذاكرة
            chat = client.chats.create(model=target_model, config=config, history=history)
            response = chat.send_message(content_parts)
            
            st.session_state.request_count += 1 
            return response.text

    except Exception as e:
        if "429" in str(e):
            st.warning("🔄 نظام التهدئة: انتظر 10 ثوانٍ...")
            time.sleep(10)
            return "⚠️ تعذر التنفيذ بسبب ضغط الطلبات، يرجى المحاولة مرة أخرى."
        return f"❌ خطأ تقني: {str(e)}"

# --- [3] واجهة المستخدم ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide")

with st.sidebar:
    st.title("🛡️ مركز القيادة")
    st.progress(min(st.session_state.request_count / 50, 1.0))
    st.caption(f"الطلبات: {st.session_state.request_count} / 50")
    
    provider = st.radio("المزود:", ["Google Gemini"]) # تم التركيز على Gemini لقدراته المتعددة
    selected_model = st.selectbox("الموديل:", list(model_map.keys()))
    selected_expert = st.selectbox("الوكيل التنفيذي:", list(expert_map.keys()))
    
    live_search = st.toggle("رادار البحث الحي 📡", value=True)
    uploaded_file = st.file_uploader("📦 رفع وسائط (PNG, JPG, PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    if st.button("🗑️ تطهير السجل"):
        st.session_state.messages = []
        st.rerun()

# عرض الدردشة
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- [4] منطقة الإدخال ---
from streamlit_mic_recorder import mic_recorder
col_mic, col_txt = st.columns([1, 10])

with col_mic:
    audio = mic_recorder(start_prompt="🎤", stop_prompt="📤", key='unified_mic_v7')

with col_txt:
    text_input = st.chat_input("أصدر أوامرك هنا...")

# معالجة المدخلات
input_val = None
voice_flag = False
pdf_content = None

if audio:
    input_val, voice_flag = audio, True
elif text_input:
    input_val = text_input

if input_val:
    # إذا كان الملف المرفق PDF
    if uploaded_file and uploaded_file.name.endswith('.pdf'):
        with st.spinner("جاري قراءة ملف PDF..."):
            pdf_content = extract_pdf_text(uploaded_file)

    label = "🎤 [أمر صوتي]" if voice_flag else input_val
    st.session_state.messages.append({"role": "user", "content": label})
    
    with st.chat_message("user"):
        st.markdown(label)
        if uploaded_file and not uploaded_file.name.endswith('.pdf'): st.image(uploaded_file, width=200)

    with st.chat_message("assistant"):
        with st.spinner("جاري التحليل..."):
            res = run_engine(input_val, is_voice=voice_flag, image_data=uploaded_file if not pdf_content else None, pdf_text=pdf_content)
            st.markdown(res)
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.download_button("💾 تصدير التقرير", res, file_name="report.txt")
