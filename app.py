import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, os
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والواجهة (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.12.0", layout="wide", page_icon="🎤")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; background-color: #111; }
    .stSelectbox label, .stSlider label { color: #00ffcc !important; font-weight: bold; }
    /* تنسيق تدفق النص */
    .stChatMessage { transition: all 0.5s ease; }
    </style>
    """, unsafe_allow_html=True)

# الربط التقني
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. القائمة الجانبية ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.12.0")
    
    # ميزة البث من الإنترنت (جديد)
    st.subheader("🌐 الاتصال المباشر")
    web_search_enabled = st.toggle("تفعيل البحث في الإنترنت (Live)", value=True)
    
    st.divider()
    
    st.subheader("🎤 المغرفون")
    audio_record = mic_recorder(
        start_prompt="بدء التسجيل", 
        stop_prompt="إرسال الصوت", 
        just_once=True, 
        key='sidebar_mic'
    )
    
    st.divider()

    thinking_level = st.select_slider("🧠 مستوى التفكير:", options=["Low", "Medium", "High"], value="High")
    persona = st.selectbox("👤 اختيار الخبير:", ["المعرفون (أهل العلم)", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"])
    
    engine_choice = st.selectbox("🎯 المحرك:", ["gemini-2.0-flash", "gemini-1.5-pro"])
    uploaded_file = st.file_uploader("📂 رفع الملفات:", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- 3. إدارة الذاكرة والسياق (Context) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

def get_history():
    """تحويل التاريخ لتنسيق Gemini"""
    history = []
    for msg in st.session_state.messages:
        role = "model" if msg["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [msg["content"]]})
    return history

# عرض الرسائل السابقة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# --- 4. معالجة المدخلات والبحث المباشر ---
prompt = st.chat_input("اطلب أخبار اليوم، الطقس، أو أي سؤال مباشر...")

if prompt or audio_record or uploaded_file:
    user_txt = prompt if prompt else "🎤 [تم إرسال أمر صوتي]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        try:
            # إعداد ميزة البحث المباشر (Google Search Tool)
            tools = [{"google_search_retrieval": {}}] if web_search_enabled else []
            
            model = genai.GenerativeModel(
                model_name=engine_choice,
                tools=tools
            )
            
            # بدء محادثة مع السياق (لتذكر ما قيل سابقاً)
            chat = model.start_chat(history=get_history())
            
            # بناء الطلب النهائي
            full_prompt = f"بصفتك {persona} وبمستوى تفكير {thinking_level}: {user_txt}"
            
            # معالجة الوسائط (صور/ملفات)
            input_data = [full_prompt]
            if uploaded_file:
                if uploaded_file.type.startswith("image"):
                    input_data.append(Image.open(uploaded_file))
                else:
                    input_data.append(uploaded_file.read().decode())
            
            # تنفيذ البث النصي (Streaming)
            response_placeholder = st.empty()
            full_response = ""
            
            # جلب الرد بنظام التدفق
            response = chat.send_message(input_data, stream=True)
            
            for chunk in response:
                full_response += chunk.text
                response_placeholder.markdown(full_response + "▌")
            
            response_placeholder.markdown(full_response)
            
            # نطق الرد آلياً
            if full_response:
                tts = gTTS(text=full_response[:300], lang='ar')
                audio_fp = io.BytesIO()
                tts.write_to_fp(audio_fp)
                st.audio(audio_fp, format='audio/mp3')
            
            # حفظ الرد في الذاكرة
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"فشل في المعالجة: {e}")
