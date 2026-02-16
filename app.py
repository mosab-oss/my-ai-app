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

# --- [1] أسطول الموديلات ومجلس الخبراء الكامل ---
model_map = {
    "Gemini 3 Flash": "gemini-3-flash-preview",
    "Gemini 3 Pro": "gemini-3-pro-preview",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
    "Gemini 1.5 Flash": "gemini-flash-latest"
}

expert_map = {
    "🌍 خبير عام": "أنت مستشار عام ذكي، تجيب بدقة ووضوح ولباقة.",
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

if "request_count" not in st.session_state: st.session_state.request_count = 0
if "messages" not in st.session_state: st.session_state.messages = []

# --- [2] إدارة الاتصال والمحرك التنفيذي (حماية الحصة والتبديل الذكي) ---
def get_gemini_client():
    try:
        return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except:
        return None

def run_engine(prompt_data, is_voice=False, image_data=None):
    target_model = model_map.get(selected_model, "gemini-flash-latest")
    expert_instruction = expert_map.get(selected_expert, "خبير عام")

    try:
        if provider == "Google Gemini":
            client = get_gemini_client()
            if not client: return "🚨 فشل في الاتصال بالخادم."

            config = types.GenerateContentConfig(
                system_instruction=expert_instruction,
                tools=[types.Tool(google_search=types.GoogleSearch())] if live_search else None,
                temperature=0.7
            )

            content_list = []
            if image_data: content_list.append(Image.open(image_data))
            if is_voice:
                content_list.append(types.Part.from_bytes(data=prompt_data['bytes'], mime_type="audio/wav"))
            else:
                content_list.append(prompt_data)

            response = client.models.generate_content(model=target_model, contents=content_list, config=config)
            
            # تحديث الحصة عند النجاح فقط
            st.session_state.request_count += 1 
            return response.text

        elif provider == "DeepSeek AI":
            client = OpenAI(api_key=st.secrets.get("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": expert_instruction}, {"role": "user", "content": prompt_data}]
            )
            st.session_state.request_count += 1
            return response.choices[0].message.content

    except Exception as e:
        if "429" in str(e):
            st.warning("🔄 نظام التهدئة: انتظر 15 ثانية (بدون خصم من حصتك)...")
            time.sleep(15)
            return run_engine(prompt_data, is_voice, image_data)
        return f"❌ خطأ تقني: {str(e)}"

# --- [3] واجهة المستخدم الاحترافية ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide")

# كود التنسيق البصري (CSS)
st.markdown("""
     <style>
    /* جعل الخلفية العامة داكنة جداً */
    .stApp { 
        background-color: #0e1117; 
        color: #ffffff !important; 
        direction: rtl; 
        text-align: right; 
    }
    
    /* تنسيق فقاعات الدردشة: نص أسود على خلفية فاتحة أو نص أبيض على خلفية داكنة */
    .stChatMessage { 
        background-color: #262730 !important; /* لون رمادي داكن للفقاعة */
        border-right: 5px solid #007bff !important; 
        border-radius: 15px !important;
        color: #ffffff !important; /* نص أبيض ناصع للرؤية */
        margin-bottom: 10px;
    }

    /* إصدار أمر لجعل كل النصوص داخل التطبيق واضحة */
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #ffffff !important;
    }

    /* تحسين شكل زر التصدير ليبرز أكثر */
    .stDownloadButton button {
        background-color: #155724 !important;
        color: #d4edda !important;
        border: 1px solid #c3e6cb !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)
with st.sidebar:
    st.title("🛡️ مركز القيادة")
    st.progress(min(st.session_state.request_count / 50, 1.0))
    st.caption(f"الطلبات الناجحة: {st.session_state.request_count} / 50")
    
    st.divider()
    provider = st.radio("المزود الاستراتيجي:", ["Google Gemini", "DeepSeek AI"])
    selected_model = st.selectbox("الموديل:", list(model_map.keys()), index=3)
    selected_expert = st.selectbox("الوكيل التنفيذي:", list(expert_map.keys()))
    
    st.divider()
    live_search = st.toggle("رادار البحث الحي 📡", value=True)
    uploaded_file = st.file_uploader("📦 رفع وسائط أو ملفات", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    if st.button("🗑️ تطهير السجل"):
        st.session_state.messages = []
        st.rerun()

# عرض الرسائل
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- [4] منطقة الإدخال الذكية (الميكروفون الدائم + النص) ---
from streamlit_mic_recorder import mic_recorder
col_mic, col_txt = st.columns([1, 10])

with col_mic:
    # ميكروفون ثابت وسريع الاستجابة
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
    label = "🎤 [أمر صوتي تم استقباله]" if voice_flag else input_val
    st.session_state.messages.append({"role": "user", "content": label})
    with st.chat_message("user"):
        st.markdown(label)
        if uploaded_file: st.image(uploaded_file, width=300)

    with st.chat_message("assistant"):
        with st.spinner(f"جاري التنفيذ بواسطة {selected_expert}..."):
            res = run_engine(input_val, is_voice=voice_flag, image_data=uploaded_file)
            st.markdown(res)
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.download_button("💾 تصدير التقرير التنفيذي", res, file_name="alliance_empire_report.txt")
