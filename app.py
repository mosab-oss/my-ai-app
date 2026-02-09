import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import io

# --- 1. إعدادات الهوية والواجهة (تصحيح الخطأ السابق) ---
st.set_page_config(page_title="التحالف الفائق v19", layout="wide", page_icon="🔱")

st.markdown("""
    <style>
    .stApp { background-color: #050a10; color: #e0e0e0; }
    .main-header { font-size: 35px; color: #00d4ff; text-align: center; text-shadow: 0 0 10px #00d4ff; }
    .brain-card { background: rgba(0, 212, 255, 0.05); border: 1px solid #00d4ff; padding: 15px; border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True) # تم التصحيح هنا من input إلى html

# --- 2. تعريف العقول والمولدات ---
BRAINS = {
    "المبرمج (DeepSeek)": "خبير الأكواد وتطوير الأنظمة.",
    "المحلل (Gemini Pro)": "خبير قراءة الـ PDF والجداول الضخمة.",
    "الخبير الأمني (Coder)": "خبير فك التشفير وحماية البيانات.",
    "المخطط (Strategic)": "خبير وضع خطط العمل والمشاريع.",
    "المبدع (Flash)": "خبير الصور والوسائط المتعددة.",
    "المدقق (Qwen)": "خبير مراجعة الأخطاء والمنطق الصيني.",
    "المتحدث (Orator)": "خبير التقارير النهائية والصوت."
}

# --- 3. الشريط الجانبي (غرفة التحكم) ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/144/shield.png", width=80)
    st.title("🛡️ ترسانة التحالف")
    
    selected_brain = st.selectbox("🧠 اختر العقل القائد:", list(BRAINS.keys()))
    
    st.subheader("🚀 المحركات النشطة")
    engine = st.selectbox("المحرك المولد:", [
        "Gemini 2.0 Flash (سريع)", 
        "Gemini 1.5 Pro (عميق)", 
        "DeepSeek-V3 (برمجي)", 
        "Qwen-Max (منطقي)"
    ])
    
    uploaded_file = st.file_uploader("📂 ارفع ملف (PDF/Excel/Image)", type=['pdf', 'xlsx', 'png', 'jpg'])

# --- 4. الهيكل الرئيسي للبرنامج ---
st.markdown('<p class="main-header">🔱 نظام السبع عقول والمولدات العالمية</p>', unsafe_allow_html=True)

# عرض حالة العقول
cols = st.columns(7)
for i, name in enumerate(BRAINS.keys()):
    with cols[i]:
        status = "🟢" if name == selected_brain else "⚪"
        st.write(f"{status}\n{name.split()[0]}")

st.divider()

# سجل المحادثة
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 5. منطق معالجة الطلبات ---
if prompt := st.chat_input("أمرك مطاع يا مصعب..."):
    # إضافة رسالة المستخدم
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # رد النظام (التحالف)
    with st.chat_message("assistant"):
        with st.spinner(f"🔄 جاري تشغيل {selected_brain} عبر {engine}..."):
            # محاكاة الرد (سيتم ربطه بـ API Keys الخاصة بك)
            full_response = f"**تحليل {selected_brain}:**\n\nبناءً على المحرك {engine}، تم استلام طلبك. نحن الآن في وضع الاستعداد الكامل لمعالجة البيانات."
            
            if "برمج" in prompt or "كود" in prompt:
                full_response += "\n\n```python\n# كود مولد بواسطة DeepSeek\nprint('التحالف يعمل بكفاءة')\n```"
            
            st.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

# --- 6. عرض تفاصيل العقل النشط ---
st.info(f"💡 **مهمة العقل الحالي:** {BRAINS[selected_brain]}")
