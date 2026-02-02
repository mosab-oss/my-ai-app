import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# إعداد الصفحة
st.set_page_config(page_title="مصعب AI المتطور", page_icon="🚀")

# تحميل مفتاح الـ API
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("لم يتم العثور على مفتاح الـ API. تأكد من إعداده في الـ Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# واجهة المستخدم الجانبية
with st.sidebar:
    st.title("⚙️ الإعدادات")
    model_choice = st.radio(
        "اختر المحرك:",
        ["gemini-2.5-flash", "gemma-3-27b-it", "توليد الصور (Imagen 3)"],
        index=0
    )
    st.info("ملاحظة: محرك الصور يفضل الوصف بالإنجليزية.")

# منطق عمل التطبيق
if model_choice == "توليد الصور (Imagen 3)":
    st.header("🎨 صانع الصور الذكي")
    st.write("اكتب وصفاً لما تريد رسمه، وسأقوم بتحويل خيالك إلى حقيقة.")
    
    prompt = st.text_area("وصف الصورة (Prompt):", placeholder="مثلاً: A futuristic city with flying cars at sunset...")
    
    if st.button("إبدأ الرسم 🖌️"):
        if prompt:
            with st.spinner("جاري الرسم... قد يستغرق الأمر ثوانٍ قليلة"):
                try:
                    # استدعاء نموذج الصور
                    image_model = genai.GenerativeModel("imagen-3.0-generate-001")
                    result = image_model.generate_content(prompt)
                    
                    # عرض الصورة
                    # ملاحظة: بعض إصدارات المكتبة تعيد الصورة كبايتات مباشرة
                    st.image(result.candidates[0].content.parts[0].inline_data.data, caption="الصورة الناتجة بواسطة مصعب AI")
                    st.success("تم الرسم بنجاح!")
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الرسم: {e}")
        else:
            st.warning("الرجاء إدخال وصف للصورة.")

else:
    # محرك الدردشة (للنماذج النصية)
    st.header(f"💬 الدردشة الذكية ({model_choice})")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # عرض تاريخ المحادثة
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # إدخال المستخدم
    if prompt := st.chat_input("بماذا يمكنني مساعدتك اليوم؟"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("جاري التفكير..."):
                try:
                    model = genai.GenerativeModel(model_choice)
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"خطأ في المحرك: {e}")
