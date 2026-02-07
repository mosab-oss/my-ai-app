import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, requests
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الواجهة والسمات ---
st.set_page_config(page_title="منصة مصعب v16.24.0", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { background-color: #000c18; direction: rtl; border-left: 2px solid #00d4ff; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; font-family: 'Courier New', monospace; }
    </style>
    """, unsafe_allow_html=True)

API_KEY = st.secrets.get("GEMINI_API_KEY")

# --- 2. محرك التنفيذ الصامت للأكواد ---
def execute_logic(text):
    display_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
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

# --- 3. القائمة الجانبية (تم التحديث لـ 2.5 Flash) ---
with st.sidebar:
    st.title("🛡️ مركز التحكم v16.24")
    audio_record = mic_recorder(start_prompt="تحدث الآن", stop_prompt="إرسال", key='v24_mic')
    st.divider()

    # تحديث القائمة: جعل gemini-2.5-flash هو الخيار الأول
    engine_choice = st.selectbox(
        "🎯 اختر المحرك:", 
        ["gemini-2.5-flash", "gemini-3-pro-preview", "gemini-3-flash", "deepseek-r1", "kimi-latest", "ernie-5.0"]
    )

    persona = st.selectbox("👤 اختيار الخبير:", ["المعرفون", "مدرس اللغة", "مساعد مبرمج", "وكيل تنفيذ"])
    st.divider()

    # زر الفحص المطور
    col_check, col_clear = st.columns(2)
    with col_check:
        if st.button("🔍 فحص الأنظمة"):
            with st.spinner("جاري الفحص..."):
                try:
                    c_test = genai.Client(api_key=API_KEY)
                    # فحص جاهزية الموديل الجديد
                    c_test.models.get(model="gemini-2.5-flash")
                    st.toast("✅ Gemini 2.5 Flash: جاهز")
                except: st.toast("❌ Google API: فشل الاتصال")
                
                if "deepseek" in engine_choice:
                    try:
                        resp = requests.get("http://localhost:1234/v1/models", timeout=2)
                        st.toast("✅ DeepSeek (Local): نشط") if resp.status_code == 200 else st.toast("⚠️ DeepSeek: السيرفر يعمل بلا موديل")
                    except: st.toast("❌ DeepSeek: شغل LM Studio")
    
    with col_clear:
        if st.button("🗑️ مسح", type="primary"):
            st.session_state.messages = []
            st.rerun()

# --- 4. معالجة الرد بتوجيه المسارات ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("اسأل التحالف العالمي...") or audio_record:
    user_txt = prompt if prompt else "🎤 [أمر صوتي]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            final_response = ""
            sys_instruct = f"أنت {persona}. إذا طلبت كود استخدم SAVE_FILE: name | content={{}}."

            # مسار Gemini الجديد (2.5 وما فوق)
            if "gemini" in engine_choice or "gemma" in engine_choice:
                client = genai.Client(api_key=API_KEY)
                res = client.models.generate_content(
                    model=engine_choice,
                    contents=user_txt,
                    config=types.GenerateContentConfig(system_instruction=sys_instruct)
                )
                final_response = res.text

            # مسار DeepSeek (محلي)
            elif "deepseek" in engine_choice:
                local_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
                res = local_client.chat.completions.create(
                    model="deepseek-r1",
                    messages=[{"role": "system", "content": sys_instruct}, {"role": "user", "content": user_txt}]
                )
                final_response = res.choices[0].message.content

            clean_txt, exec_res = execute_logic(final_response)
            st.markdown(clean_txt)
            if exec_res: st.markdown(f'<div class="exec-box">{exec_res}</div>', unsafe_allow_html=True)
            
            # الرد الصوتي
            tts = gTTS(text=clean_txt[:250], lang='ar')
            fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)
            st.session_state.messages.append({"role": "assistant", "content": clean_txt})

        except Exception as e:
            st.error(f"خطأ في الاتصال: {e}")
