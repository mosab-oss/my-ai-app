import streamlit as st
from google import genai
from google.genai import types
import os, json

# --- 1. مصفوفة العقول (تحديث المسميات للمسار الطويل لضمان عدم حدوث 404) ---
# ملاحظة: جربنا المسار القصير وفشل، الآن نستخدم المسار الكامل
MODELS_GRID = {
    "Gemini 3 Flash": "models/gemini-2.0-flash", 
    "Gemini 2.5 Flash": "models/gemini-1.5-flash",
    "Gemini 1.5 Pro": "models/gemini-1.5-pro",
    "DeepSeek R1": "models/gemini-2.0-flash-exp", # مؤقتاً لحين ربط API مستقل
    "Kimi/Ernie": "models/gemini-1.5-flash" 
}

def get_super_response(engine_label, user_input, persona_type, use_search=False):
    # نأخذ المعرف الصحيح من المصفوفة
    engine_id = MODELS_GRID.get(engine_label, "models/gemini-2.0-flash")
    
    try:
        # إنشاء العميل مع تحديد النسخة v1 لضمان التوافق
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        
        search_tool = [types.Tool(google_search=types.GoogleSearch())] if use_search else None
        
        config = types.GenerateContentConfig(
            system_instruction=f"أنت {persona_type}. خاطب مصعب باحترافية.",
            tools=search_tool
        )
        
        # تنفيذ الطلب
        response = client.models.generate_content(
            model=engine_id, 
            contents=user_input, 
            config=config
        )
        return response.text

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return f"❌ خطأ 404: المحرك {engine_id} غير مستجيب. يبدو أن جوجل غيرت مسميات الـ API. جرب 'Gemini 3 Flash'."
        if "429" in error_msg:
            return "⚠️ استنفدت الحصة اليومية. يرجى الانتظار قليلاً أو تبديل الحساب."
        return f"⚠️ خطأ تقني: {error_msg}"

# --- الواجهة الجانبية ---
with st.sidebar:
    st.title("🛡️ إصلاح الرادار v30")
    if st.button("🗑️ مسح السجل"):
        st.session_state.messages = []
        st.rerun()
    
    engine_choice = st.selectbox("🎯 اختر العقل:", list(MODELS_GRID.keys()))
    web_on = st.toggle("🌐 تفعيل البحث المباشر", value=True)
    persona = st.radio("👤 الشخصية:", ["المدرس الذكي 👨‍🏫", "الخبير التقني 🛠️"])

# --- عرض النتائج ---
if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("ما هو حال الطقس في اسطنبول؟"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        res = get_super_response(engine_choice, prompt, persona, use_search=web_on)
        st.markdown(res)
        st.session_state.messages.append({"role": "assistant", "content": res})
