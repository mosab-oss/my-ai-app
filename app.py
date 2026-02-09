import streamlit as st
from google import genai
from google.genai import types

# --- 1. إعدادات الصفحة ---
st.set_page_config(page_title="رادار مصعب الذكي", page_icon="📡", layout="wide")

# إصلاح تنسيق الـ CSS (وضعناه في سطر واحد لتجنب خطأ التنسيق)
st.markdown("<style>.stChatMessage { border-radius: 15px; }</style>", unsafe_allow_input=True)

# --- 2. إدارة المفاتيح ---
def get_keys():
    keys = []
    # جلب المفاتيح من Secrets
    for i in range(1, 4):
        k = st.secrets.get(f"GEMINI_KEY_{i}")
        if k: keys.append(k)
    return keys

API_KEYS = get_keys()

# --- 3. وظيفة جلب الرد من Gemini ---
def get_ai_response(prompt):
    if not API_KEYS:
        return "❌ يرجى إضافة GEMINI_KEY_1 في إعدادات Secrets."

    for key in API_KEYS:
        try:
            client = genai.Client(api_key=key)
            # تفعيل البحث المباشر لنتائج دقيقة (طقس، أخبار)
            search_tool = types.Tool(google_search=types.GoogleSearch())
            
            config = types.GenerateContentConfig(
                system_instruction="أنت مساعد ذكي لمصعب. استخدم البحث لتقديم معلومات دقيقة.",
                tools=[search_tool]
            )

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=config
            )
            return response.text
        except Exception as e:
            if "429" in str(e): # إذا انتهت الحصة جرب المفتاح التالي
                continue
            return f"⚠️ خطأ فني: {str(e)}"
    
    return "😴 جميع المفاتيح استهلكت حصتها، عد لاحقاً."

# --- 4. واجهة المحادثة ---
st.title("📡 رادار مصعب الذكي")

if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# إدخال المستخدم
if user_input := st.chat_input("اسألني عن أي شيء..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("جاري التفكير والبحث..."):
            response = get_ai_response(user_input)
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
