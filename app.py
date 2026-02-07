import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والواجهة (RTL) ---
st.set_page_config(page_title="منصة مصعب v16.11.0", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    .stApp { direction: rtl; text-align: right; }
    code, pre { direction: ltr !important; text-align: left !important; display: block; }
    section[data-testid="stSidebar"] { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# الربط المحلي (DeepSeek)
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")

# ربط محركات جوجل
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. مركز التحكم المطور ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.11.0")
    
    engine_choice = st.selectbox(
        "🎯 اختر المحرك:",
        ["Gemini 2.5 Flash", "Gemini 3 Pro", "Gemma 3 27B", "DeepSeek R1 (محلي)"]
    )
    
    # --- الإضافة الجديدة هنا: الشخصيات المطلوبة ---
    persona = st.selectbox(
        "👤 اختر الخبير المطلوب:", 
        [
            "وكيل تنفيذ ملفات", 
            "المعرفون (خبير المعرفة العام)", 
            "خبير اللغات والترجمة", 
            "مساعد مبرمج محترف"
        ]
    )
    
    thinking_level = st.select_slider("🧠 مستوى التفكير:", options=["Low", "Medium", "High"], value="High")
    
    st.divider()
    uploaded_file = st.file_uploader("📂 ارفع ملفك:", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])
    
    # أدوات الصيانة (زر الفحص)
    st.subheader("🛠️ أدوات الصيانة")
    if st.button("🔍 فحص الموديلات النشطة"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.info("الموديلات المتاحة لحسابك حالياً:")
            st.code("\n".join(models))
        except Exception as e: st.error(f"فشل الفحص: {e}")

# --- 3. محرك الأوامر (الوكيل الذكي) ---
def clean_and_execute(text):
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    file_pattern = r'(?:SAVE_FILE:|save_file:)\s*([\w\.-]+)\s*(?:\||content=\{?)\s*(.*?)\s*\}?$'
    match = re.search(file_pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    if match:
        filename, content = match.group(1).strip(), match.group(2).strip()
        content = re.sub(r'```python|```', '', content).strip()
        try:
            with open(filename, 'w', encoding='utf-8') as f: f.write(content)
            if filename.endswith('.py'):
                res = subprocess.run(['python3', filename], capture_output=True, text=True, timeout=10)
                output = res.stdout if res.stdout else res.stderr
                return cleaned + f"\n\n--- \n ✅ **تم التنفيذ!** \n\n**النتيجة:** \n ``` \n {output} \n ```"
            return cleaned + f"\n\n--- \n ✅ تم حفظ الملف `{filename}`."
        except Exception as e: return cleaned + f"\n\n--- \n ❌ خطأ نظام: {e}"
    return cleaned

# --- 4. واجهة الدردشة ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("تحدث مع خبيرك...")

if prompt or uploaded_file:
    # صياغة التعليمات بناءً على الشخصية المختارة
    system_instructions = {
        "المعرفون (خبير المعرفة العام)": "أنت خبير موسوعي، قدم تعريفات عميقة، حقائق تاريخية، وشروحات علمية دقيقة.",
        "خبير اللغات والترجمة": "أنت بروفيسور لغويات، متخصص في الترجمة بين اللغات، تصحيح القواعد، وشرح المصطلحات المعقدة.",
        "وكيل تنفيذ ملفات": "أنت وكيل تقني، مهمتك كتابة الأكواد وتنفيذها وحفظ الملفات باستخدام صيغة SAVE_FILE.",
        "مساعد مبرمج محترف": "أنت مبرمج خبير، ركز على كفاءة الكود، شرح الخوارزميات، وحل المشكلات البرمجية."
    }
    
    instruction = system_instructions.get(persona, "")
    user_txt = prompt if prompt else "📂 [تحليل مرفق]"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        full_res = ""
        
        # محركات جوجل
        if "Gemini" in engine_choice or "Gemma" in engine_choice:
            try:
                model_map = {
                    "Gemini 3 Pro": "models/gemini-3-pro-preview",
                    "Gemini 2.5 Flash": "models/gemini-2.5-flash",
                    "Gemma 3 27B": "models/gemma-3-27b-it"
                }
                model = genai.GenerativeModel(model_map.get(engine_choice))
                
                # دمج التعليمات مع طلب المستخدم
                full_prompt = f"{instruction}\n\nطلب المستخدم: {prompt}"
                
                response = model.generate_content(full_prompt)
                full_res = clean_and_execute(response.text)
                st.markdown(full_res)
            except Exception as e: st.error(f"خطأ في المحرك: {e}")

        # محرك DeepSeek المحلي
        elif "DeepSeek" in engine_choice:
            try:
                # (كود DeepSeek المكتمل من v16.10.1)
                pass

        if full_res:
            st.session_state.messages.append({"role": "assistant", "content": full_res})
