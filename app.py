import streamlit as st
# نقوم بالترقية للمكتبة الجديدة كلياً لدعم Gemini 3
from google import genai
from google.genai import types
import io, re, os, subprocess
from gtts import gTTS
from streamlit_mic_recorder import mic_recorder 

# --- 1. إعدادات الواجهة المتوافقة مع صورك ---
st.set_page_config(page_title="منصة مصعب v16.17.0", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    [data-testid="stSidebar"] { background-color: #001529; direction: rtl; }
    .exec-box { background-color: #000; color: #00ffcc; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# جلب المفتاح من الإعدادات (تأكد من تحديثه في Streamlit Secrets)
API_KEY = st.secrets.get("GEMINI_API_KEY")

# --- 2. دالة الفحص السريع (نسخة 2026 المطورة) ---
def fast_check_v3():
    if not API_KEY: return "❌ مفتاح API مفقود!"
    try:
        client = genai.Client(api_key=API_KEY)
        # فحص مباشر لأحدث موديل ظهر في صورتك
        client.models.get(model='gemini-3-pro-preview')
        return "✅ متصل بنجاح بجيل Gemini 3!"
    except Exception as e:
        return f"❌ خطأ في التحقق: {str(e)[:40]}"

# --- 3. القائمة الجانبية (بناءً على اختيارك في الصور) ---
with st.sidebar:
    st.title("🎮 مركز التحكم v16.17")
    
    st.subheader("🎤 المغرفون")
    audio_record = mic_recorder(start_prompt="تحدث الآن", stop_prompt="إرسال", key='v17_mic')
    
    st.divider()

    # القائمة المحدثة بالأسماء البرمجية الصحيحة لتجنب 404
    engine_choice = st.selectbox(
        "🎯 المحرك النشط:", 
        [
            "gemini-3-pro-preview", 
            "gemini-3-flash", 
            "gemini-2.0-flash",
            "deepseek-r1", # يتطلب تشغيل Server في LM Studio
            "kimi-latest",
            "ernie-bot-4"
        ]
    )

    persona = st.selectbox(
        "👤 اختيار الخبير:", 
        ["المعرفون (أهل العلم)", "مدرس اللغة", "مساعد مبرمج", "وكيل تنفيذ"]
    )

    st.divider()
    
    # صف الأزرار السريع (مسح + فحص)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔍 فحص سريع"):
            st.toast(fast_check_v3())
    with c2:
        if st.button("🗑️ مسح", type="primary"):
            st.session_state.messages = []
            st.rerun()

# --- 4. منطق التنفيذ والدردشة (بالمكتبة الجديدة) ---
# ... (استخدام client.models.generate_content)
