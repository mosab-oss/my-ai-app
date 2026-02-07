import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الواجهة (RTL والوضوح) ---
st.set_page_config(page_title="منصة مصعب v16.11.7", layout="wide", page_icon="💡")

# تنسيق CSS لضمان وضوح القائمة الجانبية
st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { background-color: #1e1e1e; color: white; direction: rtl; }
    .stSelectbox label, .stSlider label { color: #00ffcc !important; font-weight: bold; font-size: 18px; }
    code, pre { direction: ltr !important; text-align: left !important; }
    </style>
    """, unsafe_allow_html=True)

# الربط المحلي ومحركات جوجل
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية (إعادة الترتيب للظهور الفوري) ---
with st.sidebar:
    st.header("🌟 مركز التحكم v16.11.7")
    
    # وضع "المغرفون" في المقدمة لضمان الظهور
    persona = st.selectbox(
        "👤 اختر الخبير (Persona):", 
        [
            "المغرفون (خبير المعرفة العام)", 
            "خبير اللغات والترجمة", 
            "وكيل تنفيذ ملفات", 
            "مساعد مبرمج محترف"
        ],
        index=0
    )

    # وضع "مستوى التفكير" في مكان بارز
    thinking_level = st.select_slider(
        "🧠 مستوى التفكير (Thinking Level):", 
        options=["Low", "Medium", "High"], 
        value="High"
    )

    st.divider()

    # اختيار المحرك
    engine_choice = st.selectbox(
        "🎯 المحرك (Model):",
        ["Gemini 2.5 Flash", "Gemini 3 Pro", "Gemma 3 27B", "DeepSeek R1"]
    )
    
    # رفع الملفات
    uploaded_file = st.file_uploader("📂 ارفع ملفك هنا:", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    st.divider()
    
    # أدوات الصيانة والفحص
    st.subheader("🛠️ الصيانة")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 فحص الموديلات"):
            try:
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                st.info("النماذج النشطة:")
                st.code("\n".join(models))
            except Exception as e: st.error(f"خطأ: {e}")
    with col2:
        if st.button("🗑️ مسح"):
            st.session_state.messages = []
            st.rerun()

# --- 3. محرك المعالجة ---
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
                return cleaned + f"\n\n✅ **تم التنفيذ بنجاح!** \n\n ``` \n {res.stdout} \n ```"
            return cleaned + f"\n\n✅ تم حفظ الملف `{filename}`."
        except Exception as e: return cleaned + f"\n\n❌ خطأ نظام: {e}"
    return cleaned

# --- 4. واجهة المحادثة ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("تحدث مع المغرفون الآن...")

if prompt or uploaded_file:
    user_txt = prompt if prompt else "📂 [تحليل مرفق]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        full_res = ""
        # توجيهات النظام بناءً على الاختيارات
        instructions = {
            "المغرفون (خبير المعرفة العام)": f"أنت خبير موسوعي بمستوى تفكير {thinking_level}. اشرح بعمق وصوتياً.",
            "خبير اللغات والترجمة": f"أنت بروفيسور لغويات بمستوى تفكير {thinking_level}.",
            "وكيل تنفيذ ملفات": "أنت وكيل تقني ينفذ الأكواد بصيغة SAVE_FILE.",
            "مساعد مبرمج محترف": "أنت مبرمج خبير يحل المشكلات بكفاءة."
        }
        
        try:
            model_map = {"Gemini 3 Pro": "models/gemini-3-pro-preview", "Gemini 2.5 Flash": "models/gemini-2.5-flash", "Gemma 3 27B": "models/gemma-3-27b-it"}
            model = genai.GenerativeModel(model_map.get(engine_choice, "models/gemini-2.5-flash"))
            
            response = model.generate_content(f"{instructions.get(persona)}\n\n{user_txt}")
            full_res = clean_and_execute(response.text)
            st.markdown(full_res)
            
            # ميزة التكلم التلقائي للمغرفون
            if "المغرفون" in persona:
                clean_audio_text = re.sub(r'[*#`]', '', full_res)
                tts = gTTS(text=clean_audio_text[:500], lang='ar')
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                st.audio(audio_fp, format='audio/mp3')
            
            st.session_state.messages.append({"role": "assistant", "content": full_res})
        except Exception as e: st.error(f"خطأ: {e}")
