import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io, re, os, subprocess
from gtts import gTTS
from PIL import Image
from streamlit_mic_recorder import mic_recorder 

# --- 1. الإعدادات والواجهة ---
st.set_page_config(page_title="منصة مصعب v16.9.8", layout="wide")

# الربط مع المحرك المحلي
local_client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")

# إعداد Gemini
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# --- 2. مركز التحكم ---
with st.sidebar:
    st.header("🎮 مركز التحكم v16.9.8")
    
    # تحديث المسميات بناءً على صورتك من AI Studio
    engine_choice = st.selectbox(
        "🎯 اختر المحرك:",
        ["Gemini 3 Pro Preview", "Gemini 2.5 Flash", "DeepSeek R1 (محلي)"]
    )
    
    # زر تشخيصي لحل مشكلة الـ 404 نهائياً
    if st.button("🔍 فحص الموديلات المتاحة لـ API"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write("الموديلات التي تدعمها بصمتك حالياً:")
            st.code("\n".join(models))
        except Exception as e:
            st.error(f"فشل الفحص: {e}")

    st.divider()
    uploaded_file = st.file_uploader("📂 ارفع ملف:", type=["pdf", "csv", "txt", "jpg", "png", "jpeg"])

# --- 3. دالة التنفيذ (تدعم صيغة مصعب وصيغة جيمناي) ---
def clean_and_execute(text):
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    # البحث عن الأوامر
    file_pattern = r'(?:SAVE_FILE:|save_file:)\s*([\w\.-]+)\s*(?:\||content=\{?)\s*(.*?)\s*\}?$'
    match = re.search(file_pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    if match:
        filename, content = match.group(1).strip(), match.group(2).strip()
        content = re.sub(r'```python|```', '', content).strip()
        try:
            with open(filename, 'w', encoding='utf-8') as f: f.write(content)
            if filename.endswith('.py'):
                res = subprocess.run(['python3', filename], capture_output=True, text=True, timeout=10)
                return cleaned + f"\n\n--- \n ✅ **نفذتُ الكود!** \n\n**الناتج:** \n ``` \n {res.stdout if res.stdout else res.stderr} \n ```"
            return cleaned + f"\n\n--- \n ✅ حفظتُ الملف: `{filename}`"
        except Exception as e: return cleaned + f"\n\n--- \n ❌ خطأ: {e}"
    return cleaned

# --- 4. المعالجة ---
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("تحدث مع نظامك...")

if prompt or uploaded_file:
    user_txt = prompt if prompt else "تحليل ملف"
    st.session_state.messages.append({"role": "user", "content": user_txt})
    with st.chat_message("user"): st.markdown(user_txt)

    with st.chat_message("assistant"):
        if "Gemini" in engine_choice:
            try:
                # التصحيح النهائي للمسميات بناءً على تحديثات 2026
                model_map = {
                    "Gemini 3 Pro Preview": "gemini-3-pro-preview", # الاسم الظاهر في صورتك
                    "Gemini 2.5 Flash": "gemini-2.5-flash"        # الاسم الظاهر في صورتك
                }
                
                selected_model = model_map.get(engine_choice)
                model = genai.GenerativeModel(model_name=selected_model)
                
                # إرسال الطلب
                response = model.generate_content(prompt)
                full_res = clean_and_execute(response.text)
                st.markdown(full_res)
                st.session_state.messages.append({"role": "assistant", "content": full_res})
            except Exception as e:
                st.error(f"خطأ 404 (لا يزال الموديل غير مطابق): {e}")
                st.info("اضغط على زر 'فحص الموديلات' في القائمة الجانبية للتأكد من المسمى الصحيح.")
