import streamlit as st
import os
import time
import io
import base64
from google import genai
from google.genai import types
from openai import OpenAI  # لاستدعاء DeepSeek
from PIL import Image

# --- [1] إعدادات الواجهة الملكية (الوضع الداكن الفاخر) ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505 !important; color: #FFFFFF !important; direction: rtl; }
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2 { color: #FFFFFF !important; }
    .stChatMessage { background-color: #1a1a1a !important; border-right: 5px solid #007bff !important; border-radius: 12px; }
    .stDownloadButton button { background-color: #28a745 !important; color: white !important; width: 100%; border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- [2] أسطول الموديلات المطور (إضافة DeepSeek R1) ---
model_map = {
    "🧠 DeepSeek R1 (محرك الاستدلال العميق)": "deepseek-reasoner", # هذا هو المطلوب
    "📈 Gemini 2.5 Pro (القوة المتوازنة)": "gemini-2.5-pro",
    "🚀 Gemini 3 Flash (السرعة القصوى)": "gemini-3-flash-preview",
    "🛡️ Gemini 3 Pro (التحليل الاستراتيجي)": "gemini-3-pro-preview",
    "📡 Gemini 1.5 Flash (الرادار المستقر)": "gemini-flash-latest"
}

expert_map = {
    "📈 محلل أسواق": "أنت بروفيسور مالي عالمي. استخدم البحث الحي وجوباً لجلب أسعار الذهب والبورصة والعملات الآن، وقدم تحليلاً في جداول.",
    "🛡️ خبير استراتيجي": "أنت محلل عسكري وسياسي رفيع المستوى، تقدم رؤى استراتيجية وسيناريوهات مستقبلية.",
    "⚖️ مستشار قانوني": "أنت خبير قانوني مراجع للعقود والامتثال للقوانين الدولية.",
    "💻 خبير تقني": "أنت مبرمج خبير، وظيفتك كتابة الأكواد النظيفة وحل المشكلات المعقدة.",
    "📧 خبير المراسلات": "أنت سكرتير تنفيذي، تصيغ الخطابات الرسمية والإيميلات بلهجة دبلوماسية احترافية.",
    "🌍 خبير عام": "أنت مستشار ذكي موسوعي، تجيب بوضوح ولباقة."
}

if "messages" not in st.session_state: st.session_state.messages = []
if "count" not in st.session_state: st.session_state.count = 0

# --- [3] المحرك التنفيذي المزدوج (Google + DeepSeek) ---
def run_empire_engine(user_input, is_voice=False, uploaded_file=None):
    try:
        # إذا كان الموديل المختار هو DeepSeek
        if "DeepSeek" in selected_model:
            client = OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": expert_map[selected_expert]},
                    {"role": "user", "content": user_input if not is_voice else "[صوت غير مدعوم في DeepSeek حالياً]"}
                ]
            )
            st.session_state.count += 1
            return response.choices[0].message.content

        # إذا كان الموديل من عائلة Gemini
        else:
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            search_tool = types.Tool(google_search=types.GoogleSearch())
            config = types.GenerateContentConfig(
                system_instruction=expert_map.get(selected_expert),
                tools=[search_tool] if live_search else [],
                temperature=0.7
            )
            parts = []
            if uploaded_file: parts.append(Image.open(uploaded_file))
            if is_voice:
                parts.append(types.Part.from_bytes(data=user_input['bytes'], mime_type="audio/wav"))
                parts.append(f"أنت {selected_expert}. استخدم البحث الحي فوراً.")
            else:
                parts.append(f"{user_input} (استخدم البحث الحي الآن)")
            
            response = client.models.generate_content(model=model_map[selected_model], contents=parts, config=config)
            st.session_state.count += 1
            return response.text

    except Exception as e:
        return f"❌ تنبيه تقني: {str(e)}"

# --- [4] بناء الواجهة والتحكم ---
with st.sidebar:
    st.title("🛡️ مركز القيادة")
    st.success(f"الطلبات: {st.session_state.count} / 50")
    selected_model = st.selectbox("اختر المحرك:", list(model_map.keys()), index=0)
    selected_expert = st.selectbox("الوكيل التنفيذي:", list(expert_map.keys()))
    live_search = st.toggle("رادار البحث الحي 📡", value=True)
    up_file = st.file_uploader("رفع وسائط", type=['png', 'jpg', 'jpeg'])

# عرض المحادثة
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# منطقة الإدخال
from streamlit_mic_recorder import mic_recorder
c1, c2 = st.columns([1, 8])
with c1:
    audio_data = mic_recorder(start_prompt="🎤", stop_prompt="📤", key='empire_mic_v10')
with c2:
    text_data = st.chat_input("أصدر أوامرك هنا...")

active_input = None
is_audio = False
if audio_data: active_input, is_audio = audio_data, True
elif text_data: active_input = text_data

if active_input:
    label = "🎤 [أمر صوتي]" if is_audio else active_input
    st.session_state.messages.append({"role": "user", "content": label})
    with st.chat_message("user"): st.markdown(label)
    
    with st.chat_message("assistant"):
        with st.spinner(f"جاري التفكير بواسطة {selected_model}..."):
            ans = run_empire_engine(active_input, is_audio, up_file)
            st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            st.download_button("💾 تصدير التقرير", ans, file_name="report.txt")
