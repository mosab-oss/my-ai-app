import streamlit as st
# المكتبة الجديدة لدعم Gemini 3 والسرعة القصوى
from google import genai
from google.genai import types
import io, re, os, subprocess, time
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الواجهة (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.17.5", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { background-color: #001529; direction: rtl; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: monospace; }
    .stChatFloatingInputContainer { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# جلب المفتاح من Secrets
API_KEY = st.secrets.get("GEMINI_API_KEY")

# --- 2. محرك التنفيذ الذكي للأكواد (الموجود في v16.14.5) ---
def execute_logic(text):
    # تنظيف الرد من وسوم التفكير
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
                # تنفيذ الكود وجلب النتيجة
                res = subprocess.run(['python3', fname], capture_output=True, text=True, timeout=10)
                exec_output = f"🖥️ ناتج التنفيذ:\n{res.stdout}\n{res.stderr}"
            else:
                exec_output = f"✅ تم حفظ الملف: {fname}"
        except Exception as e: exec_output = f"❌ خطأ برمي: {e}"
    return display_text, exec_output

# --- 3. القائمة الجانبية (كل الميزات + التحالف السداسي) ---
with st.sidebar:
    st.title("🎮 مركز القيادة v16.17.5")
    
    # أ. المغرفون
    st.subheader("🎤 المغرفون")
    audio_record = mic_recorder(start_prompt="تحدث الآن", stop_prompt="إرسال", key='v17_mic')
    
    st.divider()

    # ب. المحركات (تشمل Gemini 3 و Kimi و ERNIE)
    engine_choice = st.selectbox(
        "🎯 المحرك النشط:", 
        ["gemini-3-pro-preview", "gemini-3-flash", "gemini-2.0-flash", "deepseek-r1", "kimi-latest", "ernie-4.0"]
    )

    # ج. مستوى التفكير والشخصية (تشمل مدرس اللغة)
    thinking_level = st.select_slider("🧠 مستوى التفكير:", ["Low", "Medium", "High"], value="High")
    persona = st.selectbox(
        "👤 اختيار الخبير:", 
        ["المعرفون", "مدرس اللغة (ترجمة وتعليم)", "مساعد مبرمج", "وكيل تنفيذ"]
    )

    st.divider()
    
    # د. رفع الملفات وأدوات الصيانة
    uploaded_file = st.file_uploader("📂 رفع الملفات:", type=["pdf", "txt", "py", "png", "jpg"])
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 فحص سريع"):
            try:
                client = genai.Client(api_key=API_KEY)
                client.models.get(model=engine_choice)
                st.toast("✅ المحرك جاهز!")
            except: st.toast("❌ خطأ في الاتصال")
    with col2:
        if st.button("🗑️ مسح المحادثة", type="primary"):
            st.session_state.messages = []
            st.rerun()

# --- 4. واجهة الدردشة والمعالجة ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("تحدث مع التحالف العالمي...")

# تفعيل الإدخال (نصي أو صوتي)
if prompt or audio_record:
    user_txt = prompt if prompt else "🎤 [أمر صوتي عبر المغرفون]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            client = genai.Client(api_key=API_KEY)
            
            # صياغة التعليمات بناءً على الشخصية ومستوى التفكير
            instruction = f"بصفتك {persona} وتعمل بمستوى تفكير {thinking_level}. إذا طلب منك كود استخدم SAVE_FILE: name | content={{}}."
            
            # طلب الرد من المحرك
            response = client.models.generate_content(
                model=engine_choice,
                contents=user_txt,
                config=types.GenerateContentConfig(system_instruction=instruction)
            )
            
            # المعالجة: تنظيف النص + تنفيذ الأكواد
            clean_txt, exec_res = execute_logic(response.text)
            st.markdown(clean_txt)
            
            if exec_res:
                st.markdown(f'<div class="exec-box">{exec_res}</div>', unsafe_allow_html=True)

            # هـ. النطق الصوتي (الموجود في v16.14.5)
            tts = gTTS(text=clean_txt[:250], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3')

            st.session_state.messages.append({"role": "assistant", "content": clean_txt})
        except Exception as e:
            st.error(f"حدث خطأ: {e}")
