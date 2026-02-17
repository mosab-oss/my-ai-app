import streamlit as st
import google.generativeai as genai
import io
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الهوية والواجهة ---
st.set_page_config(page_title="منصة مصعب v16.12.1", layout="wide", page_icon="🎙️")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    .stButton button { width: 100%; border-radius: 10px; font-weight: bold; }
    .mic-box { border: 2px solid #ff4b4b; padding: 10px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# الربط التقني
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. إدارة الذاكرة والسياق (Context Handling) ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# تحويل تاريخ المحادثة إلى تنسيق يفهمه Gemini
def get_gemini_history():
    history = []
    for msg in st.session_state.messages:
        role = "model" if msg["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [msg["content"]]})
    return history

# --- 3. القائمة الجانبية ---
with st.sidebar:
    st.title("🎮 مركز التحكم")
    
    st.markdown('<div class="mic-box">', unsafe_allow_html=True)
    st.subheader("🎤 المغرفون")
    audio_record = mic_recorder(start_prompt="بدء التكلم", stop_prompt="إرسال الصوت", just_once=True, key='sidebar_mic')
    st.markdown('</div>', unsafe_allow_html=True)

    thinking_level = st.select_slider("🧠 مستوى التفكير:", options=["Low", "Medium", "High"], value="High")
    persona = st.selectbox("👤 اختر الشخصية:", ["المعرفون (أهل العلم)", "خبير اللغات", "وكيل تنفيذي", "مساعد مبرمج"])
    
    st.divider()
    engine_choice = st.selectbox("🎯 المحرك:", ["Gemini 2.0 Flash", "Gemini 1.5 Pro"])
    uploaded_file = st.file_uploader("📂 رفع الملفات:", type=["pdf", "txt", "jpg", "png", "jpeg"])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []
        st.rerun()

# --- 4. واجهة الدردشة والعرض ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("اكتب سؤالك هنا...")

# معالجة المدخلات
if prompt or audio_record:
    user_txt = prompt if prompt else "🎤 [رسالة صوتية]"
    
    # عرض رسالة المستخدم فوراً
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"):
        st.markdown(user_txt)

    # --- البدء في التوليد بنظام البث (Streaming) ---
    with st.chat_message("assistant"):
        try:
            # إعداد الموديل مع السياق
            model_name = "gemini-2.0-flash" if "2.0" in engine_choice else "gemini-1.5-pro"
            model = genai.GenerativeModel(model_name)
            
            # بدء جلسة محادثة تحتوي على التاريخ السابق (السياق)
            chat_session = model.start_chat(history=get_gemini_history())
            
            # تعليمات النظام (System Instructions) مدمجة في الطلب
            instruction = f"بصفتك {persona} وبمستوى تفكير {thinking_level}: "
            
            # تنفيذ البث
            response_placeholder = st.empty() # مكان فارغ لتحديث النص كلمة بكلمة
            full_response = ""
            
            # إرسال الطلب بنظام البث
            response = chat_session.send_message(instruction + user_txt, stream=True)
            
            for chunk in response:
                full_response += chunk.text
                response_placeholder.markdown(full_response + "▌") # تأثير الكتابة
            
            response_placeholder.markdown(full_response) # النص النهائي
            
            # الرد الصوتي (اختياري)
            tts = gTTS(text=full_response[:200], lang='ar')
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            st.audio(audio_fp)
            
            # حفظ الرد في الذاكرة
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"حدث خطأ في الاتصال: {e}")
