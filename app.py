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
import fitz  # PyMuPDF لقراءة الـ PDF
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder

# --- [1] مجمع العقول العالمية الموحد ---
model_map = {
    "🇺🇸 Gemini 2.0 Flash (جوجل)": "models/gemini-2.0-flash-exp",
    "🇨🇳 DeepSeek R1 (الصين - التفكير)": "deepseek/deepseek-r1",
    "🇨🇳 Qwen 2.5 (الصين - المعرفة)": "qwen/qwen-2.5-72b-instruct",
    "🇪🇺 Mistral Large (أوروبا)": "mistralai/mistral-large",
    "🇺🇸 Claude 3.5 Sonnet (أمريكا)": "anthropic/claude-3.5-sonnet"
}

expert_map = {
    "📜 البروفيسور اللغوي العربي": "أنت مرجع في البلاغة العربية، وظيفتك صياغة الردود بأفصح بيان.",
    "🛡️ المحلل الاستراتيجي": "أنت خبير جيوسياسي وعسكري، تحلل القوى العظمى بدقة.",
    "📈 خبير الأسواق الدولية": "أنت محلل مالي، استخدم البحث الحي لجلب بيانات الذهب والبورصة.",
    "💻 كبير المهندسين": "أنت خبير برمجيات، تكتشف الثغرات وتكتب الأكواد بكفاءة."
}

# --- [2] أدوات المعالجة المتطورة ---
def get_pdf_text(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    return "".join([page.get_text() for page in doc])

def text_to_speech(text):
    tts = gTTS(text=text, lang='ar')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    return fp

# --- [3] المحرك التنفيذي العابر للقارات ---
def run_alliance_engine(prompt, image=None, pdf_text=None, audio_data=None):
    target_model = model_map[selected_model]
    system_instr = expert_map[selected_expert]
    
    try:
        if "Gemini" in selected_model:
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            content_list = [prompt]
            if image: content_list.append(image)
            if pdf_text: content_list.append(f"\nسياق ملف الـ PDF:\n{pdf_text}")
            if audio_data: content_list = [types.Part.from_bytes(data=audio_data, mime_type="audio/wav"), prompt]

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
            # تشغيل العقول العالمية الأخرى عبر OpenRouter
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=st.secrets["OPENROUTER_API_KEY"])
            res = client.chat.completions.create(
                model=target_model,
                messages=[{"role": "system", "content": system_instr}, {"role": "user", "content": prompt}]
            )
            return res.choices[0].message.content
    except Exception as e:
        return f"🚨 عطل تقني في الاتصال بالعقول الدولية: {str(e)}"

# --- [4] واجهة مركز القيادة السيادي ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide")
st.title("🏛️ إمبراطورية التحالف: مركز القوى العظمى")

with st.sidebar:
    st.header("⚙️ لوحة التحكم السيادية")
    selected_model = st.selectbox("العقل المعالج المتوفر:", list(model_map.keys()))
    selected_expert = st.selectbox("المستشار المفوض:", list(expert_map.keys()))
    live_search = st.toggle("رادار البحث اللحظي 📡", value=True)
    speak_out = st.toggle("نطق الإجابة (عربي) 🗣️", value=False)
    
    st.divider()
    uploaded_file = st.file_uploader("رفع (Image, PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])
    
    st.write("🎤 الأمر الصوتي:")
    audio = mic_recorder(start_prompt="بدء التسجيل", stop_prompt="إرسال الأمر", key='mic')

# --- [5] تنفيذ المعالجة ---
if prompt := st.chat_input("أصدر أوامرك السيادية..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        img = None
        pdf_txt = None
        
        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                pdf_txt = get_pdf_text(uploaded_file)
                st.info("📄 تمت قراءة الوثيقة بنجاح")
            else:
                img = Image.open(uploaded_file)
                st.image(img, caption="تحليل الصورة المرفقة", width=300)

        with st.spinner("جاري استحضار القوى العظمى..."):
            response = run_alliance_engine(prompt, image=img, pdf_text=pdf_txt, audio_data=audio['bytes'] if audio else None)
            st.markdown(response)
            
            if speak_out:
                audio_fp = text_to_speech(response)
                st.audio(audio_fp, format='audio/mp3')
