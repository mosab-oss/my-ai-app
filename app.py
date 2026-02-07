import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والتحسينات البصرية (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.9.7", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    code, pre { direction: ltr !important; text-align: left !important; display: block; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# الربط مع السيرفر المحلي (DeepSeek)
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")

# ربط محركات جوجل - استخدام مسميات متوافقة مع AI Studio 2026
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية (مركز التحكم v16.9.7) ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.9.7")
    
    # تحديث الخيارات بناءً على AI Studio
    engine_choice = st.selectbox(
        "🎯 اختر المحرك (AI Studio):",
        ["Gemini 3 Pro Preview", "Gemini 2.5 Flash", "DeepSeek R1 (محلي)", "Gemma 2 27B"]
    )
    
    # إضافة خيار "Thinking Level" الذي ظهر في صورتك
    thinking_level = st.select_slider("🧠 مستوى التفكير (Thinking Level):", options=["Low", "Medium", "High"], value="High")
    
    persona = st.selectbox("👤 شخصية المساعد:", ["وكيل تنفيذ صامت", "مساعد مبرمج", "محلل بيانات"])
    
    st.divider()
    uploaded_file = st.file_uploader("📂 ارفع ملف:", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    st.subheader("🎙️ الإدخال الصوتي")
    audio_record = mic_recorder(start_prompt="🎤 سجل", stop_prompt="🛑 أرسل", just_once=True, key='my_mic')

# --- 3. دالة الوكيل الذكي (صائد الأوامر) ---
def clean_and_execute(text):
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    file_pattern = r'(?:SAVE_FILE:|save_file:)\s*([\w\.-]+)\s*(?:\||content=\{?)\s*(.*?)\s*\}?$'
    match = re.search(file_pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)
    
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
                return cleaned + f"\n\n--- \n ✅ **تم الحفظ والتنفيذ!** \n\n**المخرجات:** \n ``` \n {output} \n ```"
            return cleaned + f"\n\n--- \n ✅ تم حفظ الملف `{filename}`."
        except Exception as e:
            return cleaned + f"\n\n--- \n ❌ خطأ نظام: {e}"
    return cleaned

# --- 4. واجهة الدردشة والمعالجة ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("تحدث مع نظامك...")
input_audio = audio_record['bytes'] if audio_record else None

if prompt or input_audio or uploaded_file:
    user_txt = prompt if prompt else "📂 [تحليل مرفق]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"):
        st.markdown(user_txt)

    with st.chat_message("assistant"):
        full_res = ""
        
        # معالجة محركات جوجل (الإصلاح الجذري لخطأ 404)
        if "Gemini" in engine_choice or "Gemma" in engine_choice:
            try:
                # خرائط مسميات دقيقة لتجنب أخطاء الـ API
                model_map = {
                    "Gemini 3 Pro Preview": "gemini-1.5-pro", # سيتم استدعاء النسخة المستقرة
                    "Gemini 2.5 Flash": "gemini-1.5-flash",
                    "Gemma 2 27B": "gemma-2-27b"
                }
                
                # إعداد الموديل مع مراعاة مستوى التفكير
                model = genai.GenerativeModel(model_map.get(engine_choice, "gemini-1.5-flash"))
                parts = [f"بصفتك {persona} بمستوى تفكير {thinking_level}: {prompt}" if prompt else "حلل المرفق"]
                
                if uploaded_file:
                    if uploaded_file.type.startswith("image"): parts.append(Image.open(uploaded_file))
                    else: parts.append(uploaded_file.read().decode("utf-8", errors="ignore"))
                
                response = model.generate_content(parts)
                full_res = clean_and_execute(response.text)
                st.markdown(full_res)
            except Exception as e:
                st.error(f"خطأ جوجل (تمت محاولة الإصلاح): {e}")

        # معالجة DeepSeek المحلي
        elif "DeepSeek" in engine_choice:
            try:
                stream = local_client.chat.completions.create(
                    model="deepseek-r1-distill-qwen-1.5b",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True
                )
                placeholder = st.empty()
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_res += chunk.choices[0].delta.content
                        placeholder.markdown(full_res + "▌")
                full_res = clean_and_execute(full_res)
                placeholder.markdown(full_res)
            except Exception as e: st.error(f"خطأ محلي: {e}")

        if full_res:
            st.session_state.messages.append({"role": "assistant", "content": full_res})
