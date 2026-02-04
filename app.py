import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io, urllib.parse, re, json
from PIL import Image

# 1. إعدادات المنصة V12.0 (التحكم الكامل)
st.set_page_config(page_title="منصة مصعب الاحترافية V12.0", layout="wide", page_icon="⚙️")

# إعداد المفتاح السري
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ المفتاح غير موجود في Secrets!")
    st.stop()

# --- محرك الرسم المستقر ---
def draw_image_logic(query):
    clean_prompt = re.sub(r'[^\w\s]', '', query)[:60]
    encoded = urllib.parse.quote(clean_prompt)
    return f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&seed=123"

# --- دالة الاستجابة مع دعم الاختيار اليدوي ---
def generate_response(contents, selected_model):
    # خريطة الأسماء التقنية للموديلات
    model_map = {
        "Gemini 2.5 Flash (الأسرع)": "gemini-2.5-flash-exp",
        "Gemini 3 Pro (الأذكى)": "gemini-3-pro-preview",
        "Gemma 3 27B (خبير المنطق)": "gemma-3-27b-it"
    }
    
    # إذا اختار المستخدم موديل معين يدوياً
    if selected_model != "تبديل تلقائي (الوضع الذكي)":
        try:
            model_id = model_map[selected_model]
            model = genai.GenerativeModel(model_id)
            response = model.generate_content(contents)
            return response.text, selected_model
        except Exception as e:
            st.warning(f"⚠️ المحرك {selected_model} غير متاح حالياً. جاري التبديل للتلقائي...")
    
    # نظام التبديل التلقائي (Fallback)
    auto_models = ["gemini-2.5-flash-exp", "gemini-3-pro-preview", "gemma-3-27b-it"]
    for m_id in auto_models:
        try:
            model = genai.GenerativeModel(m_id)
            response = model.generate_content(contents)
            if response.text: return response.text, f"تلقائي ({m_id})"
        except: continue
    return "عذراً، لا يوجد محرك يستجيب حالياً.", None

# 2. القائمة الجانبية (الأدوات والاختيارات)
with st.sidebar:
    st.title("💎 تحكم مصعب الكامل")
    
    # --- إضافة ميزة اختيار المحرك يدوياً ---
    selected_engine = st.selectbox("🎯 اختر محرك الذكاء الاصطناعي:", [
        "تبديل تلقائي (الوضع الذكي)",
        "Gemini 2.5 Flash (الأسرع)",
        "Gemini 3 Pro (الأذكى)",
        "Gemma 3 27B (خبير المنطق)"
    ])
    
    st.divider()
    persona = st.selectbox("👤 التخصص:", ["مدرس لغات محترف", "خبير برمجة Ubuntu", "مصمم صور إبداعي", "مساعد عام"])
    
    st.divider()
    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')
    uploaded_image = st.file_uploader("رفع صورة:", type=['jpg', 'png', 'jpeg'])
    
    if st.button("🗑️ مسح المحادثة"):
        st.session_state.messages = []; st.rerun()

# 3. عرض المحادثة
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img" in msg and msg["img"]: st.image(msg["img"])

# 4. التنفيذ ومعالجة المدخلات
user_query = st.chat_input("اكتب سؤالك هنا...")

if user_query or (audio_record and audio_record['bytes']) or uploaded_image:
    prompt = user_query if user_query else "تحليل المرفقات"
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner(f"جاري الاتصال بـ {selected_engine}..."):
            # تجهيز الطلب
            content_list = [f"أجب كـ {persona}: {prompt}"]
            if uploaded_image: content_list.append(Image.open(uploaded_image))
            
            # جلب الرد بناءً على الاختيار اليدوي
            ai_text, active_name = generate_response(content_list, selected_engine)
            
            if ai_text:
                img_url = None
                if any(w in prompt for w in ["ارسم", "صورة", "تخيل"]) or persona == "مصمم صور إبداعي":
                    img_url = draw_image_logic(prompt)
                    st.image(img_url, caption="اللوحة الفنية")
                
                st.markdown(ai_text)
                st.caption(f"🚀 المحرك المستخدم: {active_name}")
                
                # الرد الصوتي
                try:
                    tts = gTTS(text=ai_text[:200], lang='ar')
                    audio_io = io.BytesIO(); tts.write_to_fp(audio_io)
                    st.audio(audio_io)
                except: pass
                
                st.session_state.messages.append({"role": "assistant", "content": ai_text, "img": img_url})
