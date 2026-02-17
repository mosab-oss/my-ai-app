import streamlit as st
import os
import io
import base64
from google import genai
from google.genai import types
from openai import OpenAI
from PIL import Image
import arabic_reshaper
from bidi.algorithm import get_display
import fitz  # PyMuPDF
from gtts import gTTS

# --- [1] أسطول الموديلات الموحد (أسماء دقيقة للمحرك الجديد) ---
model_map = {
    "Gemini 1.5 Flash": "models/gemini-1.5-flash",
    "Gemini 1.5 Pro": "models/gemini-1.5-pro",
    "DeepSeek V3": "deepseek/deepseek-chat",
    "DeepSeek R1": "deepseek/deepseek-r1",
    "Kimi (Moonshot)": "moonshotai/moonshot-v1-8k"
}

expert_map = {
    "🌍 خبير عام": "أنت مستشار عام ذكي، تجيب بدقة ووضوح ولباقة.",
    "💻 خبير تقني": "أنت خبير برمجيات، تركز على الحلول التقنية واكتشاف الأخطاء.",
    "📈 محلل أسواق": "أنت خبير مالي، استخدم البحث الحي لجلب بيانات الذهب والبورصة.",
    "🎨 فنان رقمي": "أنت خبير في تخيل الصور ووصفها بدقة لتوليدها."
}

# --- [2] محركات المعالجة الذكية ---
def run_engine(prompt_data, is_voice=False):
    target_model_id = model_map.get(selected_model, "models/gemini-1.5-flash")
    expert_instruction = expert_map.get(selected_expert, "خبير عام")
    
    try:
        if provider == "Google Gemini":
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            config = types.GenerateContentConfig(
                system_instruction=expert_instruction,
                tools=[types.Tool(google_search=types.GoogleSearch())] if live_search else None
            )
            content = [prompt_data] if not is_voice else [types.Part.from_bytes(data=prompt_data['bytes'], mime_type="audio/wav")]
            response = client.models.generate_content(model=target_model_id, contents=content, config=config)
            return response.text
        else:
            # مسار العقول الصينية عبر OpenRouter
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=st.secrets["OPENROUTER_API_KEY"])
            res = client.chat.completions.create(model=target_model_id, messages=[{"role": "system", "content": expert_instruction}, {"role": "user", "content": str(prompt_data)}])
            return res.choices[0].message.content
    except Exception as e:
        return f"❌ فشل المحرك: {str(e)}"

# --- [3] واجهة المستخدم الاحترافية ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide")

with st.sidebar:
    st.title("🛡️ مركز القيادة")
    provider = st.radio("المزود الاستراتيجي:", ["Google Gemini", "العقول الصينية (OpenRouter)"])
    selected_model = st.selectbox("الموديل:", list(model_map.keys()))
    selected_expert = st.selectbox("الوكيل التنفيذي:", list(expert_map.keys()))
    live_search = st.toggle("رادار البحث الحي 📡", value=True)
    draw_mode = st.toggle("وضعية الرسام (DALL-E 3) 🎨", value=False)
    st.divider()
    if st.button("🗑️ تطهير السجل"):
        st.session_state.messages = []
        st.rerun()

# منطقة الإدخال
text_input = st.chat_input("أصدر أوامرك هنا يا قائد...")

if text_input:
    with st.chat_message("user"):
        st.markdown(text_input)
    
    with st.chat_message("assistant"):
        with st.spinner("جاري المعالجة..."):
            res = run_engine(text_input)
            st.markdown(res)
