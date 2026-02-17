import streamlit as st
import google.generativeai as genai
import io
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والربط ---
st.set_page_config(page_title="منصة مصعب v16.12.2", layout="wide")

api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 2. دالة جلب السياق (لأنك طلبت معرفة السياق) ---
def get_history():
    return [{"role": "user" if m["role"] == "user" else "model", 
             "parts": [m["content"]]} for m in st.session_state.messages]

# --- 3. الواجهة الجانبية ---
with st.sidebar:
    st.title("🌐 وضع البث المعلوماتي")
    web_search_on = st.toggle("تفعيل البحث في الإنترنت (Live)", value=True)
    engine_choice = st.selectbox("المحرك:", ["gemini-2.0-flash", "gemini-1.5-flash"])
    persona = st.selectbox("الشخصية:", ["المعرفون", "خبير التقنية", "مساعد مبرمج"])
    
    st.divider()
    audio_record = mic_recorder(start_prompt="🎤 تكلم الآن", stop_prompt="✅ إرسال", just_once=True)

# --- 4. معالجة الدردشة ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("اسأل عن أي شيء مباشر من الإنترنت...")

if prompt or audio_record:
    user_txt = prompt if prompt else "🎤 [رسالة صوتية]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        res_placeholder = st.empty()
        full_res = ""
        
        # تفعيل أدوات البحث إذا كان الخيار مفعلاً
        tools = [{"google_search_retrieval": {}}] if web_search_on else []
        
        try:
            model = genai.GenerativeModel(
                model_name=engine_choice,
                tools=tools # هنا دمجنا "البث المباشر من الإنترنت"
            )
            
            # بدء المحادثة مع السياق (History)
            chat = model.start_chat(history=get_history())
            
            # الطلب مع التفكير والشخصية
            full_prompt = f"بصفتك {persona}، أجب بذكاء: {user_txt}"
            
            # البث (Streaming)
            response = chat.send_message(full_prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    full_res += chunk.text
                    res_placeholder.markdown(full_res + "▌")
            
            res_placeholder.markdown(full_res)
            
            # حفظ الرد في السياق
            st.session_state.messages.append({"role": "assistant", "content": full_res})
            
            # صوت اختياري
            tts = gTTS(text=full_res[:200], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp)

        except Exception as e:
            st.error(f"عذراً، حدث خطأ: {e}")
