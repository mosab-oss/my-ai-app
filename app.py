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
import pdfplumber  # المكتبة التي ثبتها السيرفر بنجاح
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder

# --- [1] مجلس القوى العظمى (العقول العالمية) ---
model_map = {
    "🇺🇸 Gemini 2.0 Flash (البرق الأمريكي)": "models/gemini-2.0-flash-exp",
    "🇨🇳 DeepSeek R1 (الذكاء الصيني العميق)": "deepseek/deepseek-r1",
    "🇪🇺 Mistral Large (الخبير الأوروبي)": "mistralai/mistral-large",
    "🇺🇸 Claude 3.5 Sonnet (الدقة الأمريكية)": "anthropic/claude-3.5-sonnet"
}

expert_map = {
    "📜 البروفيسور اللغوي العربي": "أنت مرجع في البلاغة العربية، صغ الردود بأفصح بيان ممكن.",
    "🛡️ المستشار الاستراتيجي": "أنت محلل جيوسياسي وعسكري، تحلل توازنات القوى العالمية.",
    "📈 خبير الأسواق الدولية": "أنت محلل مالي، استخدم البحث اللحظي لبيانات الذهب والبورصة.",
    "💻 كبير المهندسين": "أنت خبير برمجيات، تكتشف الأخطاء وتصمم الحلول الذكية."
}

# --- [2] وظائف المعالجة الاحترافية ---
def process_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def text_to_speech(text):
    tts = gTTS(text=text, lang='ar')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp

# --- [3] محرك القوى العظمى (المعالج المركزي) ---
def run_alliance_engine(prompt, image=None, pdf_text=None, audio_bytes=None):
    target_model = model_map[selected_model]
    system_instr = expert_map[selected_expert]
    
    try:
        if "Gemini" in selected_model:
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            content_list = [prompt]
            if image: content_list.append(image)
            if pdf_text: content_list.append(f"\nوثيقة PDF:\n{pdf_text}")
            if audio_bytes: content_list = [types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"), prompt]

            response = client.models.generate_content(
                model=target_model,
                contents=content_list,
                config=types.GenerateContentConfig(
                    system_instruction=system_instr,
                    tools=[types.Tool(google_search=types.GoogleSearch())] if live_search else None
                )
            )
            return response.text
        else:
            # تشغيل العقول العالمية (الصينية/الأوروبية) عبر OpenRouter
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=st.secrets["OPENROUTER_API_KEY"])
            messages = [{"role": "system", "content": system_instr}, {"role": "user", "content": prompt}]
            if pdf_text: messages[1]["content"] += f"\nسياق الوثيقة: {pdf_text}"
            
            res = client.chat.completions.create(model=target_model, messages=messages)
            return res.choices[0].message.content
    except Exception as e:
        return f"🚨 عطل في الاتصال بالعقل المختارة: {str(e)}"

# --- [4] واجهة مركز القيادة العليا ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide")
st.title("🏛️ إمبراطورية التحالف: مركز القوى العظمى")

with st.sidebar:
    st.header("⚙️ لوحة السيادة")
    selected_model = st.selectbox("اختر العقل المعالج:", list(model_map.keys()))
    selected_expert = st.selectbox("المستشار المفوض:", list(expert_map.keys()))
    live_search = st.toggle("رادار البحث اللحظي 📡", value=True)
    speak_out = st.toggle("نطق الرد (عربي) 🗣️", value=False)
    
    st.divider()
    uploaded_file = st.file_uploader("ارفع وثيقة أو صورة:", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    st.write("🎤 الأمر الصوتي:")
    audio = mic_recorder(start_prompt="بدء التسجيل", stop_prompt="إرسال", key='mic')

# --- [5] المعالجة والعرض ---
if prompt := st.chat_input("أصدر أوامرك السيادية..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        img = None
        pdf_txt = None
        
        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                pdf_txt = process_pdf(uploaded_file)
                st.info("📄 تم تحليل وثيقة الـ PDF بنجاح")
            else:
                img = Image.open(uploaded_file)
                st.image(img, caption="تحليل بصري", width=300)

        with st.spinner("جاري استحضار الحكمة الدولية..."):
            response = run_alliance_engine(prompt, image=img, pdf_text=pdf_txt, audio_bytes=audio['bytes'] if audio else None)
            st.markdown(response)
            
            if speak_out:
                st.audio(text_to_speech(response), format='audio/mp3')
