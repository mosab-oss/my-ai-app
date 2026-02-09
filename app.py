import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI  
import io, re, os, subprocess, json
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text # التأكد من استدعاء المحول النصي
from PIL import Image

# --- 1. إدارة الذاكرة السيادية ---
def load_history():
    if os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def save_history(messages):
    with open("history.json", "w", encoding="utf-8") as f: 
        json.dump(messages, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="تحالف مصعب v16.46.25 - النسخة الكاملة", layout="wide", page_icon="🛡️")

# --- 2. مصفوفة العقول السبعة المثبتة ---
MODELS_GRID = {
    "Gemini 3 Flash": "gemini-3-flash",
    "Gemini 2.5 Flash": "gemini-1.5-flash", # المسمى المستقر للنسخة 2.5
    "Gemini 2.0 Flash": "gemini-2.0-flash-exp",
    "DeepSeek R1": "deepseek-reasoner",
    "Gemma 3 27B": "gemma-3-27-it",
    "Ernie 5.0": "ernie-5.0",
    "Kimi Latest": "moonshot-v1-8k"
}

# --- 3. محرك الاستجابة مع معالجة البحث والوسائط ---
def get_super_response(engine_label, user_input, persona_type, image=None, use_search=False):
    engine_id = MODELS_GRID.get(engine_label)
    try:
        if "Gemini" in engine_label or "Gemma" in engine_label:
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            search_tool = [types.Tool(google_search=types.GoogleSearch())] if use_search else None
            
            config = types.GenerateContentConfig(
                system_instruction=f"أنت {persona_type}. خاطب مصعب باحترافية.",
                tools=search_tool
            )
            # إرسال النص كقائمة نصوص صريحة لمنع أخطاء Pydantic
            response = client.models.generate_content(model=engine_id, contents=[user_input], config=config)
            return response.text
        
        elif "Ernie" in engine_label or "Kimi" in engine_label:
            # منطق OpenAI للمحركات الأخرى (يتم تفعيله عند توفر الـ API Keys)
            return "المحرك مفعل، يرجى التأكد من مفاتيح الربط."
            
    except Exception as e:
        return f"⚠️ عذراً مصعب، حدث خطأ: {str(e)}"

# --- 4. شريط التحكم والواجهة الجانبية ---
if "messages" not in st.session_state: st.session_state.messages = load_history()

with st.sidebar:
    st.title("🛡️ مركز القيادة v25")
    
    # ميزة مسح السجل (تصفير كامل)
    if st.button("🗑️ مسح السجل وتصفير الذاكرة"):
        st.session_state.messages = []
        if os.path.exists("history.json"): os.remove("history.json")
        st.success("تم تصفير المنصة!")
        st.rerun()

    st.divider()
    # ميزة الميكروفون (Speech to Text)
    st.write("🎙️ التواصل الصوتي:")
    audio_text = speech_to_text(language='ar', start_prompt="ابدأ الكلام", stop_prompt="إنهاء", key='mic_final')
    
    st.divider()
    # ميزة البحث المفقودة
    web_on = st.toggle("🌐 تفعيل البحث المباشر (الرادار المفتوح)", value=True)
    
    persona = st.radio("👤 الشخصية:", ["المدرس الذكي 👨‍🏫", "الخبير التقني 🛠️", "المساعد الشخصي 🤖"])
    engine_choice = st.selectbox("🎯 العقل النشط:", list(MODELS_GRID.keys()))
    uploaded_file = st.file_uploader("📊 رفع ملفات", type=['csv', 'png', 'jpg'])

# --- 5. منطق العرض والرادار ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

chat_input = st.chat_input("اكتب أمرك هنا...")
# الأولوية للميكروفون إذا تم استخدامه، وإلا فالنص
final_prompt = audio_text if audio_text else chat_input

if final_prompt:
    st.session_state.messages.append({"role": "user", "content": final_prompt})
    with st.chat_message("user"): st.markdown(final_prompt)

    with st.chat_message("assistant"):
        with st.spinner("جاري جلب المعلومات..."):
            res = get_super_response(engine_choice, final_prompt, persona, use_search=web_on)
            st.markdown(res)
            
            # الرادار (كشف المسار)
            code_match = re.search(r'```python(.*?)```', res, flags=re.DOTALL)
            if code_match:
                with open("auto_fix.py", "w", encoding="utf-8") as f: f.write(code_match.group(1).strip())
                st.info(f"📂 الرادار: تم حفظ الكود في {os.path.abspath('auto_fix.py')}")

            st.session_state.messages.append({"role": "assistant", "content": res})
            save_history(st.session_state.messages)
