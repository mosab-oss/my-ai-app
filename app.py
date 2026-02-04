import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io, urllib.parse, re, json
from PIL import Image

# 1. إعدادات المنصة الشاملة V12.2
st.set_page_config(page_title="منصة مصعب الاحترافية V12.2", layout="wide", page_icon="🎓")

# إعداد المفتاح السري من Secrets
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

# --- دالة الاستجابة مع دعم الاختيار اليدوي والتبديل التلقائي ---
def generate_response(contents, selected_model):
    model_map = {
        "Gemini 2.5 Flash (الأسرع)": "gemini-2.5-flash-exp",
        "Gemini 3 Pro (الأذكى)": "gemini-3-pro-preview",
        "Gemma 3 27B (خبير المنطق)": "gemma-3-27b-it"
    }
    
    if selected_model != "تبديل تلقائي (الوضع الذكي)":
        try:
            model_id = model_map[selected_model]
            model = genai.GenerativeModel(model_id)
            response = model.generate_content(contents)
            return response.text, selected_model
        except:
            st.warning(f"⚠️ {selected_model} غير متاح، جاري التبديل للتلقائي...")
    
    auto_models = ["gemini-2.5-flash-exp", "gemini-3-pro-preview", "gemma-3-27b-it"]
    for m_id in auto_models:
        try:
            model = genai.GenerativeModel(m_id)
            response = model.generate_content(contents)
            if response.text: return response.text, f"تلقائي ({m_id})"
        except: continue
    return "لا يوجد استجابة حالياً.", None

# 2. القائمة الجانبية (الأدوات والتحكم)
with st.sidebar:
    st.title("💎 تحكم مصعب الشامل")
    
    # اختيار المحرك
    selected_engine = st.selectbox("🎯 اختر محرك الذكاء الاصطناعي:", [
        "تبديل تلقائي (الوضع الذكي)",
        "Gemini 2.5 Flash (الأسرع)",
        "Gemini 3 Pro (الأذكى)",
        "Gemma 3 27B (خبير المنطق)"
    ])
    
    st.divider()
    # اختيار التخصص
    persona = st.selectbox("👤 التخصص:", ["مدرس لغات محترف", "خبير برمجة Ubuntu", "مصمم صور إبداعي", "مساعد عام"])
    
    persona_instr = {
        "مدرس لغات محترف": "أنت مدرس لغات خبير. صحح الأخطاء، اشرح القواعد، وانطق الكلمات بوضوح.",
        "خبير برمجة Ubuntu": "أنت خبير لينكس وبرمجة. قدم حلولاً برمجية لجهاز HP.",
        "مصمم صور إبداعي": "أنت فنان رقمي بصري.",
        "مساعد عام": "أنت مساعد شامل."
    }

    st.divider()
    # المايك ورفع الملفات
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

# 4. التنفيذ (المعالج الرئيسي)
user_query = st.chat_input("تحدث مع مدرسك أو اطلب رسماً...")

if user_query or (audio_record and audio_record['bytes']) or uploaded_image:
    prompt = user_query if user_query else "حلل هذا المحتوى"
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("جاري المعالجة..."):
            # تجهيز المحتوى
            content_list = [f"بصفتك {persona}، نفذ الآتي: {prompt}"]
            if uploaded_image: content_list.append(Image.open(uploaded_image))
            
            # جلب الرد
            ai_text, active_name = generate_response(content_list, selected_engine)
            
            if ai_text:
                # أ- معالجة الصور
                img_url = None
                if any(w in prompt for w in ["ارسم", "صورة", "تخيل"]) or persona == "مصمم صور إبداعي":
                    img_url = draw_image_logic(prompt)
                    st.image(img_url, caption="اللوحة الفنية")
                
                # ب- عرض النص
                st.markdown(ai_text)
                st.caption(f"🚀 المحرك: {active_name}")
                
                # ج- زر النطق الصوتي (مدمج وذكي)
                try:
                    # تنظيف النص للنطق
                    clean_voice_text = re.sub(r'[^\w\s.,!?]', '', ai_text)
                    # تحديد اللغة تلقائياً (الإنجليزية إذا وجد حروف لاتينية)
                    lang_code = 'en' if re.search(r'[a-zA-Z]', clean_voice_text) else 'ar'
                    
                    tts = gTTS(text=clean_voice_text[:300], lang=lang_code)
                    audio_io = io.BytesIO()
                    tts.write_to_fp(audio_io)
                    st.audio(audio_io, format='audio/mp3')
                except Exception as e:
                    pass # تخطي إذا فشل الصوت لضمان استمرار النص
                
                # حفظ في الذاكرة
                st.session_state.messages.append({"role": "assistant", "content": ai_text, "img": img_url})
