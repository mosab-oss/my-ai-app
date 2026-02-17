import streamlit as st
from google import genai
from google.genai import types
from openai import OpenAI

# --- [1] إعدادات الهوية والجمالية العربية ---
st.set_page_config(page_title="إمبراطورية التحالف 2026", layout="wide", page_icon="🏛️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Cairo', sans-serif; text-align: right; direction: rtl; }
    .stChatFloatingInputContainer { direction: ltr; }
    .stSidebar { background-color: #1e1e1e; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- [2] مجمع العقول السيادية (بدون الصيني) ---
model_map = {
    "🇺🇸 Gemini 2.0 (جوجل - للبحث الحي)": "models/gemini-1.5-flash",
    "🇺🇸 Claude 3.5 (أنتثروبيك - للدقة اللغوية)": "anthropic/claude-3.5-sonnet",
    "🇪🇺 Mistral Large (أوروبا - للتحليل المنطقي)": "mistralai/mistral-large"
}

# --- [3] مجلس المستشارين والمدربين ---
expert_map = {
    "🛡️ المستشار الاستراتيجي": "أنت جنرال ومحلل جيوسياسي، تحلل المواقف برؤية قيادية عسكرية وتاريخية.",
    "📈 المحلل المالي": "أنت خبير أسواق عالمي، تتابع الذهب والبورصة وتستخدم رادار البحث اللحظي.",
    "👨‍🏫 البروفيسور التعليمي": "أنت مدرس قدير، تشرح أعقد المفاهيم بتبسيط مذهل ولغة عربية سليمة.",
    "⚖️ المستشار القانوني": "أنت فقيه قانوني، تراجع العقود والأنظمة بذكاء وحرص شديد.",
    "💻 الخبير التقني": "أنت كبير مهندسين، وظيفتك حل المشاكل البرمجية وتصميم الأنظمة."
}

# --- [4] محرك الاستشارة المركزي ---
def run_council_engine(user_query, model_name, expert_role):
    system_instr = expert_map[expert_role]
    
    try:
        if "Gemini" in model_name:
            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=user_query,
                config=types.GenerateContentConfig(
                    system_instruction=system_instr,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            return response.text
        else:
            # عقول OpenRouter (Claude / Mistral)
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=st.secrets["OPENROUTER_API_KEY"])
            res = client.chat.completions.create(
                model=model_map[model_name],
                messages=[
                    {"role": "system", "content": system_instr},
                    {"role": "user", "content": user_query}
                ]
            )
            return res.choices[0].message.content
    except Exception as e:
        return f"🚨 عذراً يا قائد، المستشار مشغول حالياً: {str(e)}"

# --- [5] واجهة مركز القيادة ---
st.title("🏛️ إمبراطورية التحالف: مجلس الخبراء")

with st.sidebar:
    st.header("👤 اختيار المستشار")
    selected_expert = st.selectbox("من تريد استشارته؟", list(expert_map.keys()))
    
    st.divider()
    st.header("🧠 العقل المعالج")
    selected_model = st.radio("اختر المحرك الذكي:", list(model_map.keys()))
    
    st.divider()
    st.success("✅ النظام يعمل بأرقى العقول الأمريكية والأوروبية.")

# إدارة الذاكرة وسجل المحادثة
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# إدخال الأوامر
if prompt := st.chat_input("تحدث مع المستشار..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(f"جاري تحضير {selected_expert}..."):
            answer = run_council_engine(prompt, selected_model, selected_expert)
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
