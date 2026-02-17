import streamlit as st
import pandas as pd
from openai import OpenAI
import io
import speech_recognition as sr
from pydub import AudioSegment
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والواجهة ---
st.set_page_config(page_title="منصة مصعب v16.11.9", layout="wide")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; background-color: #111; }
    .stStatusWidget { direction: rtl; } /* تحسين مظهر شريط الحالة */
    </style>
    """, unsafe_allow_html=True)

# الربط بـ LM Studio
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")

# --- 2. وظائف المعالجة مع إظهار الحالة ---

def transcribe_audio_fixed(audio_bytes):
    r = sr.Recognizer()
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        with sr.AudioFile(wav_io) as source:
            audio_data = r.record(source)
            # إظهار نمط "التعرف على الكلام"
            return r.recognize_google(audio_data, language='ar-SA')
    except Exception as e:
        return f"خطأ: {str(e)}"

# --- 3. إدارة الذاكرة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 4. القائمة الجانبية ---
with st.sidebar:
    st.header("🎮 مركز التحكم")
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("🎤 الميكروفون")
    audio_record = mic_recorder(start_prompt="تحدث الآن", stop_prompt="إرسال", key='mic')
    
    st.divider()
    # إظهار حالة المحرك في القائمة الجانبية
    st.success("المحرك المحلي: متصل" if local_client else "المحرك المحلي: غير متصل")

# --- 5. واجهة الدردشة ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 6. معالجة الإدخال وإظهار "أنماط الذكاء" ---
prompt = st.chat_input("اكتب سؤالك هنا...")
user_input = None

if audio_record:
    # نمط 1: جاري معالجة الصوت
    with st.status("🎤 جاري معالجة صوتك وتحويله لنص...", expanded=True) as status:
        user_input = transcribe_audio_fixed(audio_record['bytes'])
        status.update(label="✅ تم تحويل الصوت بنجاح!", state="complete", expanded=False)
elif prompt:
    user_input = prompt

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        # نمط 2: جاري التفكير (Thinking Pattern)
        with st.spinner("🧠 ذكاء DeepSeek يفكر الآن في الرد..."):
            try:
                system_instruction = "أنت مساعد ذكي تجيب بالعربية فقط."
                messages_to_send = [{"role": "system", "content": system_instruction}]
                messages_to_send.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.messages])

                stream = local_client.chat.completions.create(
                    model="deepseek-r1-distill-qwen-1.5b",
                    messages=messages_to_send,
                    stream=True,
                    temperature=0.3
                )
                # نمط 3: جاري الكتابة (Streaming Pattern)
                answer = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # نمط 4: جاري النطق الصوتي
                with st.toast("🔊 جاري تشغيل الرد الصوتي..."):
                    tts = gTTS(text=answer[:400], lang='ar')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, format='audio/mp3')
            
            except Exception as e:
                st.error(f"حدث خطأ في نمط الاتصال: {e}")
