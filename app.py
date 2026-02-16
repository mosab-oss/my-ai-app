import streamlit as st
import os
import time
import io
import base64
from google import genai
from google.genai import types
from openai import OpenAI
from PIL import Image
import arabic_reshaper
from bidi.algorithm import get_display

# --- [1] التعريفات الكاملة ---
model_map = {
    "Gemini 3 Flash": "gemini-3-flash-preview",
    "Gemini 3 Pro": "gemini-3-pro-preview",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
    "Gemini 1.5 Flash": "gemini-flash-latest"
}

expert_map = {
    "🌍 خبير عام": "أنت مستشار عام ذكي، تجيب بدقة ووضوح.",
    "💻 خبير تقني": "أنت خبير برمجيات، تركز على الحلول البرمجية.",
    "📈 محلل أسواق": "أنت خبير مالي، استخدم البحث الحي وجوباً لجلب بيانات الذهب والبورصة والعملات الآن.",
    "🛡️ خبير استراتيجي": "أنت محلل استراتيجي جيوسياسي وعسكري.",
    "⚖️ مستشار قانوني": "أنت خبير قانوني مراجع للعقود والامتثال."
}

if "request_count" not in st.session_state: st.session_state.request_count = 0
if "messages" not in st.session_state: st.session_state.messages = []

# --- [2] المحرك التنفيذي المطور (إصلاح البث الحي) ---
def get_gemini_client():
    try: return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except: return None

def run_engine(prompt_data, is_voice=False, image_data=None):
    target_model = model_map.get(selected_model, "gemini-flash-latest")
    expert_instruction = expert_map.get(selected_expert, "خبير عام")

    try:
        if provider == "Google Gemini":
            client = get_gemini_client()
            if not client: return "🚨 فشل في الاتصال بالخادم."

            # إجبار الموديل على البحث الحي
            config = types.GenerateContentConfig(
                system_instruction=expert_instruction,
                tools=[types.Tool(google_search=types.GoogleSearch())] if live_search else None,
                temperature=0.7
            )

            content_list = []
            if image_data: content_list.append(Image.open(image_data))
            
            if is_voice:
                content_list.append(types.Part.from_bytes(data=prompt_data['bytes'], mime_type="audio/wav"))
                content_list.append(f"بصفتك {selected_expert}، قم بالبحث المباشر عبر الإنترنت للإجابة على هذا التسجيل.")
            else:
                # تعزيز النص بطلب البحث الحي
                enhanced_prompt = f"{prompt_data} (يرجى استخدام البحث الحي عبر الإنترنت لإعطاء نتائج دقيقة الآن)"
                content_list.append(enhanced_prompt)

            response = client.models.generate_content(model=target_model, contents=content_list, config=config)
            st.session_state.request_count += 1 
            return response.text

    except Exception as e:
        if "429" in str(e):
            st.warning("🔄 نظام التهدئة نشط.. يتم جلب البيانات خلال 15 ثانية...")
            time.sleep(15)
            return run_engine(prompt_data, is_voice, image_data)
        return f"❌ خطأ تقني: {str(e)}"

# --- [3] واجهة المستخدم (علاج البياض والتباين) ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; direction: rtl; text-align: right; }
    .stChatMessage { border-right: 5px solid #007bff; border-radius: 10px; background-color: #1e1e1e !important; color: #ffffff !important; }
    .stMarkdown p, .stMarkdown h1, .stMarkdown h2 { color: #ffffff !important; }
    .stDownloadButton button { background-color: #28a745 !important; color: white !important; width: 100%; border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

# (تكملة بقية الكود الخاص بالواجهة والميكروفون كما هو لديك)
# ... مع التأكد من استخدام run_engine الجديدة
