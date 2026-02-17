import streamlit as st
import os
import time
import io
import base64
import requests
from google import genai
from google.genai import types
from openai import OpenAI
from PIL import Image
import arabic_reshaper
from bidi.algorithm import get_display
import fitz  # PyMuPDF
from gtts import gTTS

# --- [1] أسطول الموديلات الموحد ---
# ملاحظة: الموديلات الصينية تعمل عبر OpenRouter لضمان الشمولية
model_map = {
    "Gemini 1.5 Flash": "gemini-1.5-flash-latest",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
    "DeepSeek V3": "deepseek/deepseek-chat",
    "DeepSeek R1 (Deep Thinking)": "deepseek/deepseek-r1",
    "Kimi (Moonshot)": "moonshotai/moonshot-v1-8k",
    "Qwen 2.5 (Alibaba)": "qwen/qwen-2.5-72b-instruct"
}

expert_map = {
    "🌍 خبير عام": "أنت مستشار عام ذكي، تجيب بدقة ووضوح ولباقة.",
    "💻 خبير تقني": "أنت خبير برمجيات، تركز على الحلول البرمجية وتطوير الأكواد.",
    "📈 محلل أسواق": "أنت خبير مالي، حلل البيانات الاقتصادية وقدم رؤى استثمارية.",
    "🎨 فنان رقمي": "أنت مصمم خبير، ساعد المستخدم في تخيل الصور ووصفها بدقة للتوليد.",
    "🛡️ خبير استراتيجي": "أنت محلل استراتيجي جيوسياسي وعسكري، حلل المواقف من منظور قيادي."
}

if "request_count" not in st.session_state: st.session_state.request_count = 0
if "messages" not in st.session_state: st.session_state.messages = []

# --- [2] محركات المعالجة الذكية ---

def text_to_speech_ar(text):
    try:
        tts = gTTS(text=text, lang='ar')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

def extract_pdf_content(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "".join([page.get_text() for page in doc])

# ميزة توليد الصور عبر DALL-E 3 (OpenRouter)
def generate_image(prompt):
    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=st.secrets["OPENROUTER_API_KEY"])
        response = client.images.generate(
            model="openai/dall-e-3",
            prompt=prompt,
            n=1, size="1024x1024"
        )
        return response.data[0].url
    except Exception as e:
        return f"❌ فشل توليد الصورة: {str(e)}"

def run_engine(prompt_data, is_voice=False, image_data=None, pdf_text=None):
    target_model_id = model_map.get(selected_model)
    search_instruction = "\nاستخدم البحث الحي دائماً." if live_search else ""
    expert_instruction = expert_map.get(selected_expert, "خبير عام") + search_instruction

    try:
        # مسار Google Gemini
        if provider == "Google Gemini":
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            history = []
            for msg in st.session_state.messages[-3:]:
                role = "user" if msg["role"] == "user" else "model"
                history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

            config = types.GenerateContentConfig(
                system_instruction=expert_instruction,
                tools=[types.Tool(google_search=types.GoogleSearch())] if live_search else None,
                temperature=0.3
            )
            
            content_list = []
            if pdf_text: content_list.append(f"محتوى الـ PDF:\n{pdf_text}")
            if image_data: content_list.append(Image.open(image_data))
            
            if is_voice:
                content_list.append(types.Part.from_bytes(data=prompt_data['bytes'], mime_type="audio/wav"))
            else:
                content_list.append(prompt_data)

            chat = client.chats.create(model=target_model_id, config=config, history=history)
            response = chat.send_message(content_list)
            st.session_state.request_count += 1
            return response.text

        # مسار العقول الصينية (OpenRouter)
        else:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=st.secrets["OPENROUTER_API_KEY"])
            messages = [{"role": "system", "content": expert_instruction}]
            for msg in st.session_state.messages[-3:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            user_msg = "[أمر صوتي]" if is_voice else str(prompt_data)
            messages.append({"role": "user", "content": user_msg})

            response = client.chat.completions.create(model=target_model_id, messages=messages)
            st.session_state.request_count += 1
            return response.choices[0].message.content

    except Exception as e:
        if "402" in str(e): return "❌ رصيد العقول الصينية غير كافٍ. يرجى الشحن أو استخدام Gemini."
        return f"❌ خطأ تقني: {str(e)}"

# --- [3] الواجهة الرسومية ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; direction: rtl; text-align: right; }
    .stChatMessage { background-color: #262730 !important; border-radius: 15px; border-right: 5px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("🛡️ مركز القيادة")
    st.progress(min(st.session_state.request_count / 50, 1.0))
    st.divider()
    provider = st.radio("المزود الاستراتيجي:", ["Google Gemini", "العقول الصينية (OpenRouter)"])
    
    # تصفية الموديلات حسب المزود
    if provider == "Google Gemini":
        available_models = ["Gemini 1.5 Flash", "Gemini 2.5 Pro"]
    else:
        available_models = ["DeepSeek V3", "DeepSeek R1 (Deep Thinking)", "Kimi (Moonshot)", "Qwen 2.5 (Alibaba)"]
    
    selected_model = st.selectbox("الموديل:", available_models)
    selected_expert = st.selectbox("الوكيل التنفيذي:", list(expert_map.keys()))
    
    st.divider()
    live_search = st.toggle("رادار البحث الحي 📡", value=True)
    speak_response = st.toggle("نطق الإجابة 🔊", value=True)
    draw_mode = st.toggle("وضعية الرسام (DALL-E 3) 🎨", value=False)
    uploaded_file = st.file_uploader("📦 رفع ملفات", type=['png', 'jpg', 'pdf'])

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if "audio" in m: st.audio(m["audio"], format="audio/mp3")

# --- [4] التفاعل الذكي ---
from streamlit_mic_recorder import mic_recorder
col_mic, col_txt = st.columns([1, 10])
with col_mic: audio = mic_recorder(start_prompt="🎤", stop_prompt="📤", key='mic')
with col_txt: text_input = st.chat_input("أصدر أوامرك...")

input_val = audio if audio else text_input
voice_flag = True if audio else False

if input_val:
    # معالجة PDF
    pdf_text = None
    if uploaded_file and uploaded_file.type == "application/pdf":
        pdf_text = extract_pdf_content(uploaded_file.read())

    # عرض مدخلات المستخدم
    label = "🎤 [أمر صوتي]" if voice_flag else input_val
    st.session_state.messages.append({"role": "user", "content": label})
    with st.chat_message("user"):
        st.markdown(label)
        if uploaded_file and uploaded_file.type != "application/pdf": st.image(uploaded_file, width=300)

    # رد المساعد
    with st.chat_message("assistant"):
        # حالة 1: وضعية الرسم
        if draw_mode:
            with st.spinner("🎨 جاري رسم خيالك..."):
                img_url = generate_image(str(input_val))
                if img_url.startswith("http"):
                    st.image(img_url, caption="تم التوليد بواسطة التحالف")
                    res = "تم إنتاج الصورة بنجاح."
                else: res = img_url
                st.markdown(res)
        # حالة 2: المعالجة النصية / البحث
        else:
            with st.status("📡 جاري المعالجة والتحليل...") as status:
                res = run_engine(input_val, is_voice=voice_flag, image_data=uploaded_file, pdf_text=pdf_text)
                status.update(label="✅ اكتملت المهمة", state="complete")
            st.markdown(res)

        # الصوت والحفظ
        msg_data = {"role": "assistant", "content": res}
        if speak_response:
            audio_fp = text_to_speech_ar(res)
            if audio_fp:
                st.audio(audio_fp)
                msg_data["audio"] = audio_fp
        
        st.session_state.messages.append(msg_data)
