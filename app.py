import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, requests
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والواجهة ---
st.set_page_config(page_title="منصة مصعب v16.26.0", layout="wide")
API_KEY_GEMINI = st.secrets.get("GEMINI_API_KEY")
API_KEY_KIMI = st.secrets.get("KIMI_API_KEY")  # تأكد من إضافة هذه في Secrets
API_KEY_ERNIE = st.secrets.get("ERNIE_API_KEY")

# --- 2. محرك التوجيه الذكي (Routing Engine) ---
def get_response(engine, prompt, persona_sys):
    # مسار Gemini 2.5 & 3
    if "gemini" in engine:
        client = genai.Client(api_key=API_KEY_GEMINI)
        res = client.models.generate_content(model=engine, contents=prompt, 
                                            config=types.GenerateContentConfig(system_instruction=persona_sys))
        return res.text

    # مسار DeepSeek (عبر LM Studio المحلي)
    elif "deepseek" in engine:
        client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
        res = client.chat.completions.create(model="deepseek-r1", 
                                            messages=[{"role": "system", "content": persona_sys}, {"role": "user", "content": prompt}])
        return res.choices[0].message.content

    # مسار Kimi (Moonshot AI)
    elif "kimi" in engine:
        client = OpenAI(base_url="https://api.moonshot.cn/v1", api_key=API_KEY_KIMI)
        res = client.chat.completions.create(model="moonshot-v1-8k", 
                                            messages=[{"role": "system", "content": persona_sys}, {"role": "user", "content": prompt}])
        return res.choices[0].message.content

    # مسار ERNIE (Baidu) - يتطلب عادةً سطر طلب مختلف
    elif "ernie" in engine:
        # هنا نستخدم جسر OpenAI إذا كنت تستخدم بروتوكول متوافق أو نداء API مباشر
        return "⚠️ محرك ERNIE 5.0 يتطلب ربطاً خاصاً بـ Baidu Cloud. هل تريد تفعيل جسر الربط له؟"

    return "❌ لم يتم التعرف على المحرك"

# --- 3. واجهة المستخدم (Sidebar) ---
with st.sidebar:
    st.title("🛡️ التحالف العالمي")
    audio_record = mic_recorder(start_prompt="🎤 المغرفون", stop_prompt="إرسال", key='v26_mic')
    
    engine_choice = st.selectbox(
        "🎯 المحرك النشط:", 
        ["gemini-2.5-flash", "gemini-3-pro-preview", "deepseek-r1", "kimi-latest", "ernie-5.0"]
    )
    
    persona = st.selectbox("👤 الخبير:", ["المعرفون", "مدرس اللغة", "مساعد مبرمج"])
    
    if st.button("🗑️ مسح"):
        st.session_state.messages = []
        st.rerun()

# --- 4. التنفيذ والدردشة ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt_input := st.chat_input("تحدث مع المحرك المختار...") or audio_record:
    user_txt = prompt_input if prompt_input else "🎤 [أمر صوتي]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            sys_msg = f"أنت {persona}. أجب باللغة العربية."
            full_reply = get_response(engine_choice, user_txt, sys_msg)
            
            # تنظيف النص من أجل النطق
            clean_text = re.sub(r'<think>.*?</think>', '', full_reply, flags=re.DOTALL).strip()
            
            if clean_text:
                st.markdown(clean_text)
                # النطق الصوتي مع حماية
                try:
                    tts = gTTS(text=clean_text[:250], lang='ar')
                    fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)
                except: pass
            else:
                st.warning("الرد فارغ أو يحتوي على أكواد فقط.")
                
            st.session_state.messages.append({"role": "assistant", "content": clean_text})
        except Exception as e:
            st.error(f"خطأ في محرك {engine_choice}: {e}")
