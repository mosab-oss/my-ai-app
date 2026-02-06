import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والربط ---
st.set_page_config(page_title="منصة مصعب v16.5 الشاملة", layout="wide", page_icon="🎤")

# ربط المحرك المحلي
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")

# ربط محركات جوجل
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية (مركز التحكم) ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.5")
    engine_choice = st.selectbox(
        "🎯 اختر المحرك:",
        ["DeepSeek R1 (محلي)", "Gemini 2.5 Flash", "Gemini 3 Pro", "Gemma 3 27B"]
    )
    persona = st.selectbox("👤 شخصية المساعد:", ["مدرس لغوي", "مساعد مبرمج", "وكيل تنفيذ ملفات"])
    
    st.divider()
    st.subheader("🎙️ الإدخال الصوتي")
    audio_record = mic_recorder(start_prompt="🎤 ابدأ التحدث", stop_prompt="🛑 توقف وأرسل", just_once=True, key='my_mic')
    
    st.divider()
    uploaded_file = st.file_uploader("📸 تحليل الصور:", type=["jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- 3. الدوال المساعدة (دالة الوكيل المحدثة) ---
def clean_response(text):
    # تنظيف وسوم التفكير
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
    # ميزة الوكيل: البحث عن نمط الحفظ والتشغيل
    file_pattern = r'SAVE_FILE:\s*([\w\.-]+)\s*\|\s*(.*)'
    match = re.search(file_pattern, cleaned, flags=re.DOTALL)
    
    if match:
        filename = match.group(1).strip()
        content = match.group(2).strip()
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # التشغيل التلقائي إذا كان ملف بايثون
            if filename.endswith('.py'):
                result = subprocess.run(['python3', filename], capture_output=True, text=True, timeout=5)
                output = result.stdout if result.stdout else result.stderr
                return cleaned + f"\n\n--- \n ✅ **تم الحفظ والتشغيل!** \n\n**النتيجة من أوبنتو:** \n ``` \n {output} \n ```"
            return cleaned + f"\n\n--- \n ✅ تم حفظ الملف `{filename}` بنجاح."
        except Exception as e:
            return cleaned + f"\n\n--- \n ❌ خطأ في التنفيذ: {e}"
    return cleaned

# --- 4. واجهة الدردشة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 5. معالجة المدخلات (نص أو صوت) ---
prompt = st.chat_input("اكتب رسالتك هنا...")
input_audio_bytes = audio_record['bytes'] if audio_record else None

if prompt or input_audio_bytes:
    display_text = prompt if not input_audio_bytes else "🎤 [رسالة صوتية]"
    st.session_state.messages.append({"role": "user", "content": display_text})
    
    with st.chat_message("user"):
        st.markdown(display_text)
        if input_audio_bytes: st.audio(input_audio_bytes)

    with st.chat_message("assistant"):
        full_response = ""
        
        # أ. التعامل مع Gemini (استرجاع الميزة المفقودة)
        if "Gemini" in engine_choice:
            try:
                model_name = "gemini-1.5-flash-latest" if "Flash" in engine_choice else "gemini-1.5-pro"
                model = genai.GenerativeModel(model_name)
                content_to_send = []
                if prompt: content_to_send.append(prompt)
                if uploaded_file: content_to_send.append(Image.open(uploaded_file))
                if input_audio_bytes: content_to_send.append({'mime_type': 'audio/wav', 'data': input_audio_bytes})
                
                res = model.generate_content(content_to_send)
                full_response = res.text
                st.markdown(full_response)
            except Exception as e:
                st.error(f"خطأ في Gemini: {e}")

        # ب. التعامل مع DeepSeek المحلي
        elif "DeepSeek" in engine_choice:
            try:
                res = local_client.chat.completions.create(
                    model="deepseek-r1-distill-qwen-1.5b",
                    messages=[{"role": "system", "content": f"أنت {persona}. للحفظ والتشغيل استخدم: SAVE_FILE: name.py | content"}, 
                             {"role": "user", "content": prompt}],
                    stream=True
                )
                placeholder = st.empty()
                for chunk in res:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        placeholder.markdown(full_response + "▌")
                
                full_response = clean_response(full_response)
                placeholder.markdown(full_response)
            except:
                st.error("تأكد من تشغيل LM Studio!")

        # ج. الرد الصوتي (استرجاع الميزة المفقودة)
        if full_response:
            try:
                tts_text = re.sub(r'```.*?```', '', full_response, flags=re.DOTALL) # عدم قراءة الكود برمجياً
                tts = gTTS(text=tts_text[:300], lang='ar')
                audio_io = io.BytesIO()
                tts.write_to_fp(audio_io)
                st.audio(audio_io)
            except: pass
            st.session_state.messages.append({"role": "assistant", "content": full_response})
