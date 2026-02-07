import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والتحسينات البصرية (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.10.1", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    code, pre { direction: ltr !important; text-align: left !important; display: block; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# الربط مع السيرفر المحلي
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")

# ربط محركات جوجل
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية (مركز التحكم) ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.10.1")
    
    engine_choice = st.selectbox(
        "🎯 اختر المحرك المتاح:",
        ["Gemini 3 Pro (الأذكى)", "Gemini 2.5 Flash (الأسرع)", "Gemma 3 27B", "DeepSeek R1 (محلي)"]
    )
    
    thinking_level = st.select_slider("🧠 مستوى التفكير:", options=["Low", "Medium", "High"], value="High")
    persona = st.selectbox("👤 الشخصية:", ["وكيل تنفيذ صامت", "مساعد مبرمج", "محلل بيانات"])
    
    st.divider()
    uploaded_file = st.file_uploader("📂 ارفع ملف:", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    st.subheader("🛠️ أدوات الصيانة")
    if st.button("🔍 فحص الموديلات النشطة"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.info("الموديلات المتاحة لحسابك حالياً:")
            st.code("\n".join(models))
        except Exception as e:
            st.error(f"فشل الفحص: {e}")

    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- 3. دالة الوكيل التنفيذي ---
def clean_and_execute(text):
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    file_pattern = r'(?:SAVE_FILE:|save_file:)\s*([\w\.-]+)\s*(?:\||content=\{?)\s*(.*?)\s*\}?$'
    match = re.search(file_pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    if match:
        filename, content = match.group(1).strip(), match.group(2).strip()
        content = re.sub(r'```python|```', '', content).strip()
        try:
            with open(filename, 'w', encoding='utf-8') as f: f.write(content)
            if filename.endswith('.py'):
                res = subprocess.run(['python3', filename], capture_output=True, text=True, timeout=10)
                output = res.stdout if res.stdout else res.stderr
                return cleaned + f"\n\n--- \n ✅ **تم التنفيذ!** \n\n**الناتج:** \n ``` \n {output} \n ```"
            return cleaned + f"\n\n--- \n ✅ تم حفظ `{filename}`."
        except Exception as e: return cleaned + f"\n\n--- \n ❌ خطأ نظام: {e}"
    return cleaned

# --- 4. واجهة الدردشة والمعالجة ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("تحدث مع نظامك...")

if prompt or uploaded_file:
    user_txt = prompt if prompt else "📂 [تحليل مرفق]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        full_res = ""
        
        # أ. محركات جوجل (الأسماء المأخوذة من فحصك الأخير)
        if "Gemini" in engine_choice or "Gemma" in engine_choice:
            try:
                model_map = {
                    "Gemini 3 Pro (الأذكى)": "models/gemini-3-pro-preview",
                    "Gemini 2.5 Flash (الأسرع)": "models/gemini-2.5-flash",
                    "Gemma 3 27B": "models/gemma-3-27b-it"
                }
                model = genai.GenerativeModel(model_map.get(engine_choice, "models/gemini-2.5-flash"))
                parts = [f"بصفتك {persona} بمستوى {thinking_level}: {prompt}" if prompt else "حلل المرفق"]
                
                if uploaded_file:
                    if uploaded_file.type.startswith("image"): parts.append(Image.open(uploaded_file))
                    else: parts.append(uploaded_file.read().decode("utf-8", errors="ignore"))
                
                response = model.generate_content(parts)
                full_res = clean_and_execute(response.text)
                st.markdown(full_res)
            except Exception as e: st.error(f"خطأ جوجل: {e}")

        # ب. محرك DeepSeek المحلي (تم تصحيح البلوك بالكامل)
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
            except Exception as e:
                st.error(f"خطأ في الاتصال بـ LM Studio: {e}")

        # ج. حفظ وحفظ الرسالة
        if full_res:
            st.session_state.messages.append({"role": "assistant", "content": full_res})
