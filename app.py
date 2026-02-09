import streamlit as st
from google import genai

# --- الإعدادات الأساسية ---
st.set_page_config(page_title="رادار مصعب للطقس", page_icon="🌤️")

# 1. حاول الحصول على المفتاح من Secrets، وإذا لم يوجد اطلبه من الواجهة
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    api_key = st.sidebar.text_input("أدخل مفتاح API الجديد هنا:", type="password")

if api_key:
    client = genai.Client(api_key=api_key)
    
    st.title("🌤️ رادار الطقس الذكي (مصعب)")
    
    # اختيار النموذج - استخدمنا الأسماء المختصرة الأحدث
    model_name = "gemini-2.0-flash" 

    if prompt := st.chat_input("اسأل عن الطقس في أي مدينة..."):
        with st.chat_message("user"):
            st.markdown(prompt)
            
        try:
            # تفعيل البحث عبر الإنترنت تلقائياً لجلب الطقس اللحظي
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={'tools': [{'google_search': {}}]}
            )
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
                
        except Exception as e:
            st.error(f"حدث خطأ: {str(e)}")
            st.info("💡 إذا ظهر الخطأ 429، فالمفتاح استهلك حصته. جرب حساب Gmail آخر.")
else:
    st.warning("⚠️ من فضلك ضع مفتاح API في الجانب الأيسر للبدء.")
