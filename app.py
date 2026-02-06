import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات وتحسين اتجاه النص (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.9.2 الشاملة", layout="wide", page_icon="🚀")

# إضافة CSS لإصلاح مشكلة النصوص المقلوبة
st.markdown("""
    <style>
    /* جعل واجهة الدردشة والمدخلات من اليمين لليسار */
    .stApp {
        direction: rtl;
        text-align: right;
    }
    /* استثناء الأكواد البرمجية لتبقى من اليسار لليمين */
    code, pre {
        direction: ltr !important;
        text-align: left !important;
        display: block;
    }
    /* ضبط القائمة الجانبية */
    section[data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    </style>
    """, unsafe_allow_html=True)

# الربط مع LM Studio
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")

# ربط محركات جوجل
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.9.2")
    engine_choice = st.selectbox(
        "🎯 اختر المحرك:",
        ["DeepSeek R1 (محلي)", "Gemini 2.5 Flash", "Gemini 3 Pro", "Gemma 3 27B"]
    )
    persona = st.selectbox("👤 شخصية المساعد:", ["وكيل تنفيذ ملفات", "مساعد مبرمج", "محلل بيانات"])
    
    st.divider()
    uploaded_file = st.file_uploader("📂 ارفع ملف (PDF, CSV, TXT, Image):", 
                                   type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    st.subheader("🎙️ الإدخال الصوتي")
    audio_record = mic_recorder(start_prompt="🎤 سجل", stop_prompt="🛑 أرسل", just_once=True, key='my_mic')
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- 3. دالة الوكيل الذكي (النسخة المحدثة) ---
def clean_and_execute(text):
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
    # البحث عن نمط الحفظ بشكل مرن
    file_pattern = r'SAVE_FILE:\s*([\w\.-]+)\s*\|?\s*(.*)'
    match = re.search(file_pattern, cleaned, flags=re.DOTALL)
    
    if match:
        filename = match.group(1).strip()
        content = match.group(2).strip()
        content = re.sub(r'```python|```', '', content).strip()
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            if filename.endswith('.py'):
                res = subprocess.run(['python3', filename], capture_output=True, text=True, timeout=10)
                output = res.stdout if res.stdout else res.stderr
                return cleaned + f"\n\n--- \n ✅ **تم الحفظ والتنفيذ تلقائياً!** \n\n**المخرجات:** \n ``` \n {output} \n ```"
            return cleaned + f"\n\n--- \n ✅ تم حفظ الملف `{filename}`."
        except Exception as e:
            return cleaned + f"\n\n--- \n ❌ خطأ: {e}"
    return cleaned

# --- 4. واجهة الدردشة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 5. المعالجة ---
prompt = st.chat_input("تحدث مع نظامك...")
input_audio = audio_record['bytes'] if audio_record else None

if prompt or input_audio or uploaded_file:
    user_txt = prompt if prompt else "📂 [تحليل مرفق]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"):
        st.markdown(user_txt)

    with st.chat_message("assistant"):
        full_res = ""
        
        if "DeepSeek" in engine_choice:
            try:
                stream = local_client.chat.completions.create(
                    model="deepseek-r1-distill-qwen-1.5b",
                    messages=[
                        {"role": "system", "content": f"أنت {persona}. يجب أن تستخدم دائماً: SAVE_FILE: name.py | ثم الكود."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                placeholder = st.empty()
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content
                        placeholder.markdown(full_res + "▌")
                full_res = clean_and_execute(full_res)
                placeholder.markdown(full_res)
            except Exception as e:
                st.error(f"تأكد من LM Studio: {e}")

        elif any(name in engine_choice for name in ["Gemini", "Gemma"]):
            try:
                model_map = {"Gemini 2.5 Flash": "gemini-1.5-flash", "Gemini 3 Pro": "gemini-1.5-pro", "Gemma 3 27B": "gemma-2-27b"}
                model = genai.GenerativeModel(model_map.get(engine_choice, "gemini-1.5-flash"))
                parts = [f"بصفتك {persona}: {prompt}"]
                if uploaded_file:
                    if uploaded_file.type.startswith("image"): parts.append(Image.open(uploaded_file))
                    else: parts.append(uploaded_file.read().decode("utf-8", errors="ignore"))
                if input_audio: parts.append({'mime_type': 'audio/wav', 'data': input_audio})
                
                response = model.generate_content(parts)
                full_res = response.text
                st.markdown(full_res)
            except Exception as e: st.error(f"خطأ جوجل: {e}")

        if full_res:
            try:
                audio_text = re.sub(r'```.*?```', '', full_res, flags=re.DOTALL)
                tts = gTTS(text=audio_text[:250], lang='ar')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)
            except: pass
            st.session_state.messages.append({"role": "assistant", "content": full_res})
