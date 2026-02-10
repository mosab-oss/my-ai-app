import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والواجهة (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.13.5", layout="wide", page_icon="⚙️")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    section[data-testid="stSidebar"] { direction: rtl; background-color: #050a30; }
    .exec-box { background-color: #1a1a1a; color: #00ff00; padding: 15px; border-radius: 10px; border: 1px solid #00ff00; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# الربط التقني (Gemini & Local APIs)
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key: genai.configure(api_key=api_key)

# --- 2. وظيفة التنفيذ الذكي للأكواد ---
def execute_logic(text):
    # إزالة وسوم التفكير للعرض النظيف
    display_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
    # البحث عن نمط حفظ الملف SAVE_FILE: name | content={}
    file_pattern = r'SAVE_FILE:\s*([\w\.-]+)\s*\|\s*content=\{(.*?)\}'
    match = re.search(file_pattern, text, flags=re.DOTALL)
    
    exec_output = ""
    if match:
        fname, fcontent = match.group(1).strip(), match.group(2).strip()
        fcontent = re.sub(r'```python|```', '', fcontent).strip()
        try:
            with open(fname, 'w', encoding='utf-8') as f: f.write(fcontent)
            if fname.endswith('.py'):
                res = subprocess.run(['python3', fname], capture_output=True, text=True, timeout=10)
                exec_output = f"🖥️ ناتج التنفيذ:\n{res.stdout}\n{res.stderr}"
        except Exception as e: exec_output = f"❌ خطأ: {e}"
    return display_text, exec_output

# --- 3. القائمة الجانبية: "كل الميزات" في مكان واحد ---
with st.sidebar:
    st.title("🎮 غرفة التحكم v16.13.5")
    
    # أ. المغرفون (الميكروفون)
    st.subheader("🎤 المغرفون")
    audio_record = mic_recorder(start_prompt="تحدث الآن", stop_prompt="إرسال", key='main_mic')
    
    st.divider()

    # ب. التحالف العالمي (المحركات)
    engine_choice = st.selectbox(
        "🎯 اختر المحرك (العقل):", 
        ["DeepSeek R1 (محلي)", "Gemini 2.5 Flash", "Kimi AI (ذاكرة)", "ERNIE Bot (معارف)"]
    )

    # ج. مستوى التفكير والشخصية
    thinking_level = st.select_slider("🧠 مستوى التفكير:", ["Low", "Medium", "High"], value="High")
    persona = st.selectbox("👤 الشخصية:", ["المعرفون", "مساعد مبرمج", "وكيل تنفيذ"])

    st.divider()

    # د. الأدوات الإضافية (رفع الملفات وفحص الموديلات)
    uploaded_file = st.file_uploader("📂 رفع الملفات:", type=["pdf", "txt", "py", "png", "jpg"])
    
    if st.button("🔍 فحص الموديلات النشطة"):
        st.info("جاري فحص الاتصال بـ LM Studio و Gemini API...")

# --- 4. معالجة المحادثة والتنفيذ ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("تحدث مع التحالف العالمي...")

if prompt or audio_record or uploaded_file:
    user_txt = prompt if prompt else "🎤 [أمر صوتي عبر المغرفون]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            # توجيه الطلب للمحرك المختار (مثال: Gemini)
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            full_req = f"بصفتك {persona} (تفكير {thinking_level}): {user_txt}. إذا طلبت كود استخدم صيغة SAVE_FILE: name | content={{}}."
            
            response = model.generate_content(full_req)
            
            # تنظيف وتطوير الرد + التنفيذ التلقائي
            clean_txt, execution_res = execute_logic(response.text)
            st.markdown(clean_txt)
            
            if execution_res:
                st.markdown(f'<div class="exec-box">{execution_res}</div>', unsafe_allow_html=True)

            # الرد الصوتي (TTS)
            tts = gTTS(text=clean_txt[:300], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3')

            st.session_state.messages.append({"role": "assistant", "content": clean_txt})
        except Exception as e: st.error(f"عذراً، حدث خطأ: {e}")
