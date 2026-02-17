import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, time
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 
from PIL import Image

# --- 1. الإعدادات والسمات ---
st.set_page_config(page_title="منصة مصعب v16.39.0", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; background-color: #0e1117; color: white; }
    [data-testid="stSidebar"] { background-color: #000c18; border-left: 2px solid #00d4ff; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: monospace; }
    .status-badge { background-color: #1a1a1a; color: #00d4ff; border: 1px solid #00d4ff; padding: 2px 10px; border-radius: 20px; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# جلب المفاتيح السرية
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY")
KIMI_KEY = st.secrets.get("KIMI_API_KEY")
ERNIE_KEY = st.secrets.get("ERNIE_API_KEY")

# --- 2. محرك التنفيذ المطور (الحفظ الإجباري v16.39) ---
def run_execution_logic(text):
    clean_txt = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
    # البحث عن كود بايثون بين علامات التنسيق القياسية
    code_blocks = re.findall(r'```python(.*?)```', text, flags=re.DOTALL)
    
    exec_out = ""
    if code_blocks:
        for i, code in enumerate(code_blocks):
            # محاولة استخراج اسم ملف أو استخدام اسم افتراضي
            name_match = re.search(r'([\w\.-]+\.py)', text)
            fname = name_match.group(1) if name_match else f"auto_script_{i}.py"
            
            try:
                # إجبار النظام على كتابة الملف في المجلد الحالي
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write(code.strip())
                
                # تنفيذ الملف
                res = subprocess.run(['python3', fname], capture_output=True, text=True, timeout=10)
                exec_out += f"✅ تم حفظ {fname}\n🖥️ ناتج التنفيذ:\n{res.stdout}\n{res.stderr}"
            except Exception as e:
                exec_out += f"❌ خطأ في {fname}: {e}\n"
    
    return clean_txt, exec_out

# --- 3. دالة التوجيه الشاملة ---
def get_super_response(engine, user_input, persona, image=None, use_search=False):
    client = genai.Client(api_key=GEMINI_KEY)
    search_tool = [types.Tool(google_search=types.GoogleSearch())] if use_search else None

    def gemini_router(target_model):
        try:
            contents = [user_input]
            if image: contents.append(image)
            config = types.GenerateContentConfig(system_instruction=f"أنت {persona}", tools=search_tool)
            r = client.models.generate_content(model=target_model, contents=contents, config=config)
            return r.text
        except Exception as e:
            if "429" in str(e):
                p = st.empty()
                for i in range(25, 0, -1):
                    p.warning(f"⏳ زحام! انتظر {i} ثانية...")
                    time.sleep(1)
                p.empty()
                return client.models.generate_content(model=target_model, contents=[user_input]).text
            return f"❌ خطأ: {e}"

    if "gemini" in engine or "gemma" in engine:
        return gemini_router(engine)
    elif "ernie" in engine and ERNIE_KEY:
        try:
            c = OpenAI(api_key=ERNIE_KEY, base_url="https://api.baidu.com/v1")
            res = c.chat.completions.create(model="ernie-5.0", messages=[{"role": "user", "content": user_input}])
            return res.choices[0].message.content
        except: return gemini_router("gemini-2.0-flash")
    return gemini_router("gemini-2.0-flash")

# --- 4. الواجهة الجانبية المحدثة ---
with st.sidebar:
    st.title("🛡️ تحالف مصعب v16.39")
    audio = mic_recorder(start_prompt="🎤 تحدث", stop_prompt="إرسال", key='v39_mic')
    st.divider()
    
    # مستعرض الملفات (الميزة التي طلبتها للتأكد من وجود الملفات)
    st.subheader("📁 مستعرض الملفات:")
    current_files = [f for f in os.listdir(".") if f.endswith(('.py', '.png', '.csv'))]
    st.write(current_files)
    
    st.divider()
    engine_choice = st.selectbox("🎯 المحرك:", ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-3-pro-preview", "gemma-3-27b", "deepseek-r1"])
    persona = st.selectbox("👤 الشخصية:", ["مساعد مبرمج", "مدرس لغات", "محلل بيانات"])
    web_on = st.toggle("🌐 بحث إنترنت مباشر")
    uploaded_file = st.file_uploader("🖼️ رفع ملف:", type=['jpg', 'png', 'csv'])
    
    if st.button("🗑️ مسح السجل", type="primary"):
        st.session_state.messages = []; st.rerun()

# --- 5. منطق العرض ---
if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("تحدث مع نظامك المتكامل...") or audio:
    txt = prompt if prompt else "🎤 [رسالة صوتية]"
    st.session_state.messages.append({"role": "user", "content": txt})
    with st.chat_message("user"): st.markdown(txt)

    with st.chat_message("assistant"):
        img_obj = None
        if uploaded_file and uploaded_file.type.startswith('image'):
            img_obj = Image.open(uploaded_file)
        
        with st.spinner("جاري التفكير..."):
            raw_res = get_super_response(engine_choice, txt, persona, img_obj, web_on)
        
        clean_res, code_res = run_execution_logic(raw_res)
        st.markdown(clean_res)
        
        if code_res:
            st.markdown(f'<div class="exec-box">{code_res}</div>', unsafe_allow_html=True)
            # تحديث القائمة الجانبية بعد خلق ملف جديد
            st.rerun()
        
        st.session_state.messages.append({"role": "assistant", "content": clean_res})
