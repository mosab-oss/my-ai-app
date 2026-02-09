import streamlit as st
from google import genai
from google.genai import types

# --- 1. إعدادات الصفحة والهوية ---
st.set_page_config(page_title="Gemini Super Bot", page_icon="🤖", layout="wide")

# تصميم واجهة المستخدم بـ CSS بسيط
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 5px; }
    .main { background-color: #f5f7f9; }
    </style>
    """, unsafe_allow_input=True)

# --- 2. إدارة المفاتيح والحماية ---
# نضع قائمة مفاتيح لضمان عدم التوقف (Rotation)
def get_all_keys():
    keys = []
    for i in range(1, 4):  # يبحث عن GEMINI_KEY_1, GEMINI_KEY_2, GEMINI_KEY_3
        k = st.secrets.get(f"GEMINI_KEY_{i}")
        if k: keys.append(k)
    return keys

API_KEYS = get_all_keys()

# --- 3. العقل المحرك (وظيفة توليد الرد) ---
def ask_gemini(prompt, history):
    if not API_KEYS:
        return "❌ خطأ: لم يتم ضبط مفاتيح API في Secrets."

    # محاولة التنفيذ عبر المفاتيح المتاحة
    for key in API_KEYS:
        try:
            client = genai.Client(api_key=key)
            
            # تفعيل البحث المباشر (Google Search Tool)
            search_tool = types.Tool(google_search=types.GoogleSearch())
            
            config = types.GenerateContentConfig(
                system_instruction="""أنت مساعد ذكي ومدرس خبير لمصعب. 
                أجب بدقة، وإذا سأل عن أخبار أو طقس استخدم البحث المباشر. 
                تحدث بلهجة سورية خفيفة ومحببة عند الضرورة.""",
                tools=[search_tool],
                temperature=0.7
            )

            response = client.models.generate_content(
                model="gemini-2.0-flash", # أحدث نسخة مستقرة لتجنب 404
                contents=prompt,
                config=config
            )
            return response.text
        
        except Exception as e:
            # إذا كان الخطأ بسبب الحصة (429) ننتقل للمفتاح التالي
            if "429" in str(e):
                continue
            else:
                return f"⚠️ حدث خطأ تقني: {str(e)}"
    
    return "😴 يبدو أن جميع المفاتيح استهلكت حصتها اليومية. حاول لاحقاً."

# --- 4. بناء واجهة المستخدم ---
st.title("🤖 نظام مصعب للذكاء الاصطناعي")
st.caption("نسخة شاملة تجمع كل ميزات التحديثات السابقة")

# القائمة الجانبية (Sidebar)
with st.sidebar:
    st.header("⚙️ لوحة التحكم")
    st.info(f"عدد المفاتيح المتصلة: {len(API_KEYS)}")
    if st.button("🗑️ مسح السجل"):
        st.session_state.chat_history = []
        st.rerun()
    st.divider()
    st.write("تم التطوير بواسطة مصعب و Gemini")

# إدارة ذاكرة الدردشة
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# عرض الرسائل السابقة من الذاكرة
for message in st.session_state.messages if "messages" in st.session_state else []:
     pass # كود العرض المعتاد

# عرض المحادثة
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# منطقة الإدخال
if user_input := st.chat_input("كيف يمكنني مساعدتك اليوم؟"):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        response = ask_gemini(user_input, st.session_state.messages)
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
