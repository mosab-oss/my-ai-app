import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder # استيراد الميكروفون

# --- 1. الإعدادات والربط ---
st.set_page_config(page_title="منصة مصعب v16.4", layout="wide", page_icon="🎤")

# ربط المحرك المحلي
local_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# ربط محركات جوجل
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية (إضافة الميكروفون) ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.4")
    
    engine_choice = st.selectbox(
        "🎯 اختر المحرك:",
        ["Gemini 2.5 Flash", "Gemini 3 Pro", "DeepSeek R1 (محلي)", "Gemma 3 27B"]
    )
    
    persona = st.selectbox("👤 شخصية المساعد:", ["مدرس لغوي", "مساعد مبرمج", "محلل ذكي"])
    
    st.divider()
    st.subheader("🎙️ الإدخال الصوتي")
    # إضافة زر الميكروفون
    audio_record = mic_recorder(
        start_prompt="🎤 ابدأ التحدث",
        stop_prompt="🛑 توقف وأرسل",
        just_once=True,
        key='my_mic'
    )
    
    st.divider()
    uploaded_file = st.file_uploader("📸 تحليل الصور:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- 3. الدوال المساعدة ---
def clean_response(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=st.DOTALL).strip()

# --- 4. واجهة الدردشة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(clean_response(msg["content"]))

# --- 5. معالجة المدخلات (نص أو صوت) ---
prompt = st.chat_input("اكتب رسالتك هنا...")

# إذا تم التسجيل عبر الميكروفون، نعتبره هو المدخل (Prompt)
input_audio_bytes = None
if audio_record:
    input_audio_bytes = audio_record['bytes']
    prompt = "تحليل تسجيل صوتي" # نص افتراضي للتعامل مع الصوت

if prompt or input_audio_bytes:
    # إضافة رسالة المستخدم
    display_text = prompt if not input_audio_bytes else "🎤 [رسالة صوتية]"
    st.session_state.messages.append({"role": "user", "content": display_text})
    
    with st.chat_message("user"):
        st.markdown(display_text)
        if input_audio_bytes:
            st.audio(input_audio_bytes)

    with st.chat_message("assistant"):
        full_response = ""
        
        # أ. التعامل مع Gemini (يدعم الصوت والصور)
        if "Gemini" in engine_choice:
            try:
                model_name = "gemini-1.5-flash-latest" if "Flash" in engine_choice else "gemini-3-pro-preview"
                model = genai.GenerativeModel(model_name)
                
                content_to_send = []
                if prompt: content_to_send.append(prompt)
                if uploaded_file: content_to_send.append(Image.open(uploaded_file))
                if input_audio_bytes:
                    content_to_send.append({'mime_type': 'audio/wav', 'data': input_audio_bytes})
                
                res = model.generate_content(content_to_send)
                full_response = res.text
                st.markdown(full_response)
            except Exception as e:
                st.error(f"خطأ في Gemini: {e}")

        # ب. التعامل مع DeepSeek المحلي (نصوص فقط حالياً)
        elif "DeepSeek" in engine_choice:
            if input_audio_bytes:
                st.warning("DeepSeek المحلي لا يدعم تحليل الصوت مباشرة، يرجى استخدام Gemini للصوت.")
            else:
                try:
                    res = local_client.chat.completions.create(
                        model="deepseek-r1-distill-qwen-7b",
                        messages=[{"role": "system", "content": f"أنت {persona}"}, {"role": "user", "content": prompt}],
                        stream=True
                    )
                    placeholder = st.empty()
                    for chunk in res:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            placeholder.markdown(full_response + "▌")
                    placeholder.markdown(clean_response(full_response))
                except: st.error("تأكد من تشغيل LM Studio!")

        # ج. الرد الصوتي التلقائي (الذكاء يتحدث إليك)
        if full_response:
            try:
                clean_text = clean_response(full_response)
                tts = gTTS(text=clean_text[:300], lang='ar')
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                st.audio(audio_io)
            except: pass
            st.session_state.messages.append({"role": "assistant", "content": full_response})
