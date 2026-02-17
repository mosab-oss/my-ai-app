import streamlit as st
from google import genai
from google.genai import types
import io, re, os, subprocess
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الواجهة (Professional Dark Theme) ---
st.set_page_config(page_title="منصة مصعب v16.20.0", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #000c18; direction: rtl; border-left: 1px solid #00d4ff; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: 'Courier New', monospace; }
    .stChatFloatingInputContainer { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# جلب مفتاح API من Secrets
API_KEY = st.secrets.get("GEMINI_API_KEY")

# --- 2. محرك التنفيذ الذكي للأكواد ---
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
                # تشغيل الكود في عملية فرعية وجلب الناتج
                res = subprocess.run(['python3', fname], capture_output=True, text=True, timeout=15)
                exec_output = f"🖥️ ناتج التنفيذ:\n{res.stdout}\n{res.stderr}"
            else:
                exec_output = f"✅ تم حفظ الملف بنجاح: {fname}"
        except Exception as e: exec_output = f"❌ خطأ أثناء التنفيذ: {e}"
    return display_text, exec_output

# --- 3. القائمة الجانبية (Sidebar): التحالف السباعي ---
with st.sidebar:
    st.title("🛡️ التحالف السباعي v16.20")
    
    # أ. ميزة المغرفون
    st.subheader("🎤 المغرفون")
    audio_record = mic_recorder(start_prompt="تحدث الآن", stop_prompt="إرسال الصوت", key='v20_gold_mic')
    
    st.divider()

    # ب. القائمة النهائية الموحدة كما طلبت
    engine_choice = st.selectbox(
        "🎯 اختر العقل المفكر:", 
        [
            "gemini-3-pro-preview", 
            "gemini-3-flash", 
            "gemini-2.5-flash", 
            "deepseek-r1", 
            "kimi-latest", 
            "ernie-5.0", 
            "gemma-3-27b"
        ]
    )

    # ج. مستوى التفكير والشخصيات
    thinking_level = st.select_slider("🧠 مستوى التفكير:", ["Low", "Medium", "High"], value="High")
    persona = st.selectbox(
        "👤 تقمص دور:", 
        ["المعرفون (أهل العلم)", "مدرس اللغة (ترجمة وتعليم)", "مساعد مبرمج محترف", "وكيل تنفيذ"]
    )

    st.divider()
    
    # د. أدوات الصيانة السريعة
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 فحص"):
            try:
                client = genai.Client(api_key=API_KEY)
                client.models.get(model="gemini-1.5-flash") # فحص سريع للاتصال
                st.toast("✅ الاتصال أخضر ومستقر!")
            except: st.toast("❌ خطأ: تأكد من API Key")
    with c2:
        if st.button("🗑️ مسح", type="primary"):
            st.session_state.messages = []
            st.rerun()

# --- 4. واجهة المحادثة والمعالجة الذكية ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# إدخال المستخدم (نص أو صوت)
prompt = st.chat_input("تحدث مع التحالف السباعي...")

if prompt or audio_record:
    user_txt = prompt if prompt else "🎤 [أمر صوتي عبر المغرفون]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            client = genai.Client(api_key=API_KEY)
            
            # صياغة التعليمات البرمجية للنظام
            sys_instruct = f"أنت تلعب دور {persona} وتفكر بمستوى {thinking_level}. إذا طلب منك كود برمجيا، استخدم حصراً صيغة: SAVE_FILE: name | content={{}}."
            
            # إرسال الطلب للمحرك (استخدام محرك استدلال قوي كقاعدة)
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=user_txt,
                config=types.GenerateContentConfig(system_instruction=sys_instruct)
            )
            
            # معالجة الرد: التنظيف من التفكير + تنفيذ الأكواد
            clean_txt, execution_res = execute_logic(response.text)
            st.markdown(clean_txt)
            
            # عرض صندوق التنفيذ إذا وجد كود
            if execution_res:
                st.markdown(f'<div class="exec-box">{execution_res}</div>', unsafe_allow_html=True)

            # الرد الصوتي التلقائي (TTS)
            tts = gTTS(text=clean_txt[:300], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp, format='audio/mp3')

            st.session_state.messages.append({"role": "assistant", "content": clean_txt})
        except Exception as e:
            st.error(f"عذراً يا مصعب، حدث خطأ فني: {e}")
