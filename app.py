import streamlit as st
import os
import time
import io
import base64
from google import genai
from google.genai import types
from openai import OpenAI
from PIL import Image
import arabic_reshaper
from bidi.algorithm import get_display
import fitz  # مكتبة PyMuPDF لقراءة ملفات PDF
from gtts import gTTS  # ميزة الرد الصوتي

# --- [1] أسطول الموديلات ومجلس الخبراء الكامل ---
model_map = {
    "Gemini 3 Flash": "gemini-3-flash-preview",
    "Gemini 3 Pro": "gemini-3-pro-preview",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
    "Gemini 1.5 Flash": "gemini-flash-latest"
}

expert_map = {
    "🌍 خبير عام": "أنت مستشار عام ذكي، تجيب بدقة ووضوح ولباقة. تذكر دائماً سياق الحوار السابق.",
    "💻 خبير تقني": "أنت خبير برمجيات، تركز على الحلول البرمجية واكتشاف الأخطاء وتطوير الأكواد.",
    "📈 محلل أسواق": "أنت خبير مالي، استخدم البحث الحي لجلب بيانات الذهب والبورصة والعملات وتحليلها.",
    "📧 مساعد المراسلات": "أنت سكرتير تنفيذي، صغ إيميلات احترافية وردود دبلوماسية بناءً على المعطيات.",
    "📊 محلل إحصائي": "أنت بروفيسور بيانات، حلل الأرقام والجداول المستخرجة وقدم رؤية إحصائية دقيقة.",
    "✍️ خبير محتوى": "أنت كاتب محترف، حول الأفكار والمسودات إلى تقارير ومقالات متكاملة.",
    "📚 خبير لغوي": "أنت بروفيسور لغوي، ركز على النحو والبلاغة العربية والتدقيق اللغوي.",
    "🛡️ خبير استراتيجي": "أنت محلل استراتيجي جيوسياسي وعسكري، حلل المواقف من منظور قيادي.",
    "⚖️ مستشار قانوني": "أنت خبير قانوني، مراجع للعقود والوثائق الرسمية والامتثال."
}

# دالة تصحيح عرض اللغة العربية
def fix_ar(text):
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
    except:
        return text

# دالة استخراج النص من ملفات PDF
def extract_pdf_content(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# دالة توليد الرد الصوتي
def text_to_speech_ar(text):
    try:
        tts = gTTS(text=text, lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except Exception as e:
        st.error(f"خطأ في توليد الصوت: {e}")
        return None

if "request_count" not in st.session_state: st.session_state.request_count = 0
if "messages" not in st.session_state: st.session_state.messages = []

# --- [2] إدارة الاتصال والمحرك التنفيذي المطور ---
def get_gemini_client():
    try:
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except:
        return None

def run_engine(prompt_data, is_voice=False, image_data=None, pdf_text=None):
    target_model = model_map.get(selected_model, "gemini-flash-latest")
    
    # تحسين أمر البحث الحي لضمان استجابة الرادار
    search_instruction = "\nاستخدم البحث الحي (Google Search) دائماً للحصول على أدق المعلومات الحالية." if live_search else ""
    expert_instruction = expert_map.get(selected_expert, "خبير عام") + search_instruction

    try:
        if provider == "Google Gemini":
            client = get_gemini_client()
            if not client: return "🚨 فشل في الاتصال بالخادم."

            # تقليل سياق الذاكرة لتقليل ضغط الـ 429
            history = []
            for msg in st.session_state.messages[-3:]: 
                role = "user" if msg["role"] == "user" else "model"
                history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

            config = types.GenerateContentConfig(
                system_instruction=expert_instruction,
                tools=[types.Tool(google_search=types.GoogleSearch())] if live_search else None,
                temperature=0.3 # تقليل الحرارة لزيادة دقة البحث الحي
            )

            content_list = []
            if pdf_text:
                content_list.append(f"محتوى مستند PDF المرفق:\n{pdf_text}\n\nالسؤال المطلوب حول المستند:")
            if image_data and not pdf_text:
                content_list.append(Image.open(image_data))
            
            if is_voice:
                content_list.append(types.Part.from_bytes(data=prompt_data['bytes'], mime_type="audio/wav"))
            else:
                content_list.append(prompt_data)

            # تشغيل الجلسة
            chat = client.chats.create(model=target_model, config=config, history=history)
            response = chat.send_message(content_list)
            
            st.session_state.request_count += 1 
            return response.text

        elif provider == "DeepSeek AI":
            client = OpenAI(api_key=st.secrets.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
            ds_messages = [{"role": "system", "content": expert_instruction}]
            for msg in st.session_state.messages[-5:]:
                ds_messages.append({"role": msg["role"], "content": msg["content"]})
            ds_messages.append({"role": "user", "content": str(prompt_data)})

            response = client.chat.completions.create(model="deepseek-chat", messages=ds_messages)
            st.session_state.request_count += 1
            return response.choices[0].message.content

    except Exception as e:
        if "429" in str(e):
            return "🚫 وصلت للحد الأقصى للطلبات المجانية حالياً. يرجى الانتظار دقيقة واحدة ثم إعادة المحاولة."
        return f"❌ خطأ تقني: {str(e)}"

# --- [3] واجهة المستخدم الاحترافية ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff !important; direction: rtl; text-align: right; }
    .stChatMessage { background-color: #262730 !important; border-right: 5px solid #007bff !important; border-radius: 15px !important; color: #ffffff !important; margin-bottom: 10px; }
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #ffffff !important; }
    .stDownloadButton button { background-color: #155724 !important; color: #d4edda !important; border: 1px solid #c3e6cb !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True) 

with st.sidebar:
    st.title("🛡️ مركز القيادة")
    st.progress(min(st.session_state.request_count / 50, 1.0))
    st.caption(f"الطلبات الناجحة: {st.session_state.request_count} / 50")
    
    st.divider()
    provider = st.radio("المزود الاستراتيجي:", ["Google Gemini", "DeepSeek AI"])
    selected_model = st.selectbox("الموديل:", list(model_map.keys()), index=0)
    selected_expert = st.selectbox("الوكيل التنفيذي:", list(expert_map.keys()))
    
    st.divider()
    live_search = st.toggle("رادار البحث الحي 📡", value=True)
    speak_response = st.toggle("نطق الإجابة آلياً 🔊", value=True)
    uploaded_file = st.file_uploader("📦 رفع (PNG, JPG, PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    if st.button("🗑️ تطهير السجل"):
        st.session_state.messages = []
        st.rerun()

# عرض الرسائل
for m in st.session_state.messages:
    with st.chat_message(m["role"]): 
        st.markdown(m["content"])
        if m["role"] == "assistant" and "audio" in m:
            st.audio(m["audio"], format="audio/mp3")

# --- [4] منطقة الإدخال الذكية ---
from streamlit_mic_recorder import mic_recorder
col_mic, col_txt = st.columns([1, 10])

with col_mic:
    audio = mic_recorder(start_prompt="🎤", stop_prompt="📤", key='unified_mic_v7')

with col_txt:
    text_input = st.chat_input("أصدر أوامرك هنا يا قائد...")

input_val = None
voice_flag = False

if audio:
    input_val, voice_flag = audio, True
elif text_input:
    input_val = text_input

if input_val:
    pdf_text = None
    if uploaded_file and uploaded_file.type == "application/pdf":
        with st.spinner("جاري مسح المستند ضوئياً..."):
            pdf_text = extract_pdf_content(uploaded_file.read())

    label = "🎤 [أمر صوتي]" if voice_flag else input_val
    st.session_state.messages.append({"role": "user", "content": label})
    
    with st.chat_message("user"):
        st.markdown(label)
        if uploaded_file and uploaded_file.type != "application/pdf": 
            st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        # إظهار حالة البحث الحي إذا كان مفعلاً
        if live_search:
            with st.status("📡 جاري تشغيل الرادار والبحث في الويب...", expanded=True) as status:
                st.write("🔍 جاري جلب المعلومات اللحظية...")
                res = run_engine(input_val, is_voice=voice_flag, image_data=uploaded_file, pdf_text=pdf_text)
                status.update(label="✅ تم اكتمال البحث والتحليل!", state="complete", expanded=False)
        else:
            with st.spinner(f"جاري التنفيذ بواسطة {selected_expert}..."):
                res = run_engine(input_val, is_voice=voice_flag, image_data=uploaded_file, pdf_text=pdf_text)
        
        st.markdown(res)
        
        # معالجة الصوت
        msg_data = {"role": "assistant", "content": res}
        if speak_response:
            audio_fp = text_to_speech_ar(res)
            if audio_fp:
                st.audio(audio_fp, format="audio/mp3")
                msg_data["audio"] = audio_fp
        
        st.session_state.messages.append(msg_data)
        st.download_button("💾 تصدير التقرير التنفيذي", res, file_name="alliance_empire_report.txt")
