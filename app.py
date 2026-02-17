import streamlit as st
import os
from google import genai
from google.genai import types
from openai import OpenAI

# --- [1] قائمة الموديلات بأسماء دقيقة للمحرك الجديد ---
model_map = {
    "Gemini 1.5 Flash": "gemini-1.5-flash", # تم تصحيح الاسم
    "Gemini 1.5 Pro": "gemini-1.5-pro",
    "DeepSeek V3": "deepseek/deepseek-chat",
    "DeepSeek R1": "deepseek/deepseek-r1",
    "Kimi (Moonshot)": "moonshotai/moonshot-v1-8k"
}

# --- [2] تعديل دالة المحرك لتفادي أخطاء المفاتيح ---
def run_engine(prompt_data, is_voice=False, image_data=None, pdf_text=None):
    target_model_id = model_map.get(selected_model, "gemini-1.5-flash")
    
    try:
        if provider == "Google Gemini":
            # التأكد من وجود المفتاح
            if "GEMINI_API_KEY" not in st.secrets:
                return "❌ خطأ: مفتاح GEMINI_API_KEY غير مضاف في Secrets."
                
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            # (بقية الكود الخاص بجوجل كما هو...)
            # ... تأكد من استخدام target_model_id ...
            
        else:
            # التأكد من وجود مفتاح OpenRouter
            if "OPENROUTER_API_KEY" not in st.secrets:
                return "❌ خطأ: مفتاح OPENROUTER_API_KEY غير مضاف. لا يمكن استخدام العقول الصينية أو الصور بدونها."
            
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=st.secrets["OPENROUTER_API_KEY"]
            )
            # (بقية الكود الخاص بـ OpenRouter كما هو...)

    except Exception as e:
        return f"❌ فشل المحرك: {str(e)}"
