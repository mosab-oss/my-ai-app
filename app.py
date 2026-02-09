import streamlit as st
from google import genai
from google.genai import types
import io, re, os, json, pandas as pd
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
from PIL import Image

# --- 1. الذاكرة الفولاذية ---
def load_history():
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def save_history(messages):
    with open("history.json", "w", encoding="utf-8") as f: 
        json.dump(messages, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="منصة مصعب v28 - النسخة الشاملة", layout="wide", page_icon="🛡️")

# --- 2. مصفوفة العقول السبعة (التصحيح النهائي للمسميات) ---
MODELS_GRID = {
    "Gemini 3 Flash (الأحدث)": "gemini-2.0-flash", 
    "Gemini 2.5 Flash": "gemini-1.5-flash",
    "Gemini 2.0 Flash": "gemini-2.0-flash-exp",
    "Gemini 1.5 Pro": "gemini-1.5-pro",
    "Gemma 3 27B": "gemma-2-27b-it",
    "DeepSeek R1": "deepseek-reasoner",
    "Kimi Latest": "moonshot-v1-8k"
}

# --- 3. محرك الاستجابة مع معالجة البحث ---
def get_super_response(engine_label, user_input, persona_type, use_search=False):
    engine_id = MODELS_GRID.get(engine_label, "gemini-2.0-flash")
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        # تفعيل أداة البحث المباشر
        search_tool = [types.Tool(google_search=types.GoogleSearch())] if use_search else None
        
        config = types.GenerateContentConfig(
            system_instruction=f"أنت {persona_type}. رد على مصعب بذكاء ووقار.",
            tools=search_tool
        )
        
        response = client.models.generate_content(model=engine_id, contents=[user_input], config=config)
        return response.text
    except Exception as e:
        # نظام القفز فوق الخطأ في حال تعطل أي محرك
        st.error(f"⚠️ {engine_label} يواجه ضغطاً. جرب محركاً آخر.")
        return f"خطأ تقني: {str(e)}"

# --- 4. واجهة مركز القيادة (تنسيقSidebar) ---
if "messages" not in st.session_state: st.session_state.messages = load_history()

with st.sidebar:
    st.title("🛡️ مركز العمليات v28")
    
    # 1. زر المسح (في القمة لسهولة الوصول)
    if st.button("🗑️ مسح السجل وتصفير الذاكرة", type="primary"):
        st.session_state.messages = []
        if os.path.exists("history.json"): os.remove("history.json")
        st.success("تم التصفير بنجاح!")
        st.rerun()

    st.divider()
    # 2. الميكروفون
    st.write("🎙️ الأوامر الصوتية:")
    audio_text = speech_to_text(language='ar', start_prompt="تحدث الآن", stop_prompt="إنهاء", key='v28_mic')
    
    st.divider()
    # 3. زر البحث المباشر (المعاد تفعيله)
    web_on = st.toggle("🌐 تفعيل البحث المباشر (Google Search)", value=True)
    
    st.divider()
    # 4. اختيار الشخصية والمحرك
    persona = st.radio("👤 الشخصية النشطة:", ["المدرس الذكي 👨‍🏫", "الخبير التقني 🛠️", "المساعد الشخصي 🤖"])
    engine_choice = st.selectbox("🎯 اختر العقل:", list(MODELS_GRID.keys()))
    uploaded_file = st.file_uploader("📊 رفع البيانات", type=['csv', 'png', 'jpg'])

# --- 5. منطق الحوار والرادار ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

chat_input = st.chat_input("تحدث مع نظامك المتكامل...")
final_prompt = audio_text if audio_text else chat_input

if final_prompt:
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"): st.markdown(final_prompt)

    with st.chat_message("assistant"):
        res = get_super_response(engine_choice, final_prompt, persona, use_search=web_on)
        st.markdown(res)
        
        # الرادار (كشف المسار)
        code_match = re.search(r'```python(.*?)```', res, flags=re.DOTALL)
        if code_match:
            with open("radar_output.py", "w", encoding="utf-8") as f: f.write(code_match.group(1).strip())
            st.info(f"📂 الرادار: تم حفظ الكود في {os.path.abspath('radar_output.py')}")

        st.session_state.messages.append({"role": "assistant", "content": res})
        save_history(st.session_state.messages)
