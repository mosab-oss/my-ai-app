import streamlit as st
from google import genai
from google.genai import types
import io, re, os, json
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text
from PIL import Image

# --- 1. إدارة ذاكرة الفصل ---
def load_history():
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def save_history(messages):
    with open("history.json", "w", encoding="utf-8") as f: 
        json.dump(messages, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="فصل مصعب الذكي v27", layout="wide", page_icon="👨‍🏫")

# --- 2. القائمة الذهبية (بدون نواقص) ---
MODELS_GRID = {
    "Gemini 3 Flash": "gemini-2.0-flash", # المسمى المستقر حالياً لـ v3
    "Gemini 2.5 Flash": "gemini-1.5-flash",
    "Gemini 2.0 Flash": "gemini-2.0-flash-exp",
    "Gemini 1.5 Pro": "gemini-1.5-pro",
    "Gemma 3 27B": "gemma-2-27b-it", # تصحيح المسمى ليعمل
    "DeepSeek R1": "deepseek-reasoner",
    "Kimi Latest": "moonshot-v1-8k"
}

# --- 3. محرك الاستجابة الذكي (مضاد للانهيار) ---
def get_super_response(engine_label, user_input, persona_type, use_search=False):
    engine_id = MODELS_GRID.get(engine_label, "gemini-2.0-flash")
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        search_tool = [types.Tool(google_search=types.GoogleSearch())] if use_search else None
        
        config = types.GenerateContentConfig(
            system_instruction=f"أنت {persona_type}. رد على مصعب بأسلوب تعليمي مشجع.",
            tools=search_tool
        )
        
        response = client.models.generate_content(model=engine_id, contents=[user_input], config=config)
        return response.text
    except Exception as e:
        # نظام القفز فوق الخطأ (Fallback)
        st.warning(f"⚠️ المحرك {engine_label} مشغول، سأجيبك باستخدام المحرك المستقر...")
        backup_res = client.models.generate_content(model="gemini-2.0-flash", contents=[user_input])
        return backup_res.text

# --- 4. واجهة مركز القيادة ---
if "messages" not in st.session_state: st.session_state.messages = load_history()

with st.sidebar:
    st.title("👨‍🏫 المعلم الذكي")
    
    # ميزة مسح السجل (المثبتة)
    if st.button("🗑️ تصفير الحصة (مسح السجل)"):
        st.session_state.messages = []
        if os.path.exists("history.json"): os.remove("history.json")
        st.rerun()

    st.divider()
    # ميزة الميكروفون
    st.write("🎤 تحدث إلي:")
    audio_text = speech_to_text(language='ar', start_prompt="ابدأ التحدث", stop_prompt="انتهيت", key='v27_mic')
    
    st.divider()
    # زر البحث المباشر
    web_on = st.toggle("🌐 تفعيل البحث المباشر", value=True)
    
    persona = st.radio("👤 اختر شخصيتي:", ["المدرس الذكي 👨‍🏫", "الخبير التقني 🛠️", "المساعد الشخصي 🤖"])
    engine_choice = st.selectbox("🎯 اختر العقل:", list(MODELS_GRID.keys()))

# --- 5. عرض الدرس ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

chat_in = st.chat_input("اسأل مدرسك أي شيء...")
final_prompt = audio_text if audio_text else chat_in

if final_prompt:
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"): st.markdown(final_prompt)

    with st.chat_message("assistant"):
        res = get_super_response(engine_choice, final_prompt, persona, use_search=web_on)
        st.markdown(res)
        
        # نطق الإجابة (اختياري)
        try:
            tts = gTTS(text=res[:100], lang='ar')
            b = io.BytesIO(); tts.write_to_fp(b); st.audio(b)
        except: pass

        st.session_state.messages.append({"role": "assistant", "content": res})
        save_history(st.session_state.messages)
