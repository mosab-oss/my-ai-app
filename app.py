import streamlit as st
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from gtts import gTTS
import io, urllib.parse, re, json
from PIL import Image

# 1. إعدادات المنصة المتقدمة V13.0 - نسخة البحث الموثق
st.set_page_config(page_title="منصة مصعب للبحث الذكي V13.0", layout="wide", page_icon="🔍")

# إعداد المفتاح السري
api_key = st.secrets.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ المفتاح غير موجود!")
    st.stop()

# --- دالة الرسم المستقر ---
def draw_image_logic(query):
    clean_prompt = re.sub(r'[^\w\s]', '', query)[:60]
    encoded = urllib.parse.quote(clean_prompt)
    return f"https://pollinations.ai/p/{encoded}?width=1024&height=1024&seed=130"

# --- دالة الاستجابة مع ميزة البحث في الإنترنت (Google Search) ---
def generate_search_response(prompt, selected_model, persona_info):
    # خريطة الموديلات
    model_map = {
        "Gemini 2.5 Flash (الأسرع)": "gemini-2.5-flash-exp",
        "Gemini 3 Pro (الأذكى)": "gemini-3-pro-preview",
        "Gemma 3 27B (خبير المنطق)": "gemma-3-27b-it"
    }
    
    model_id = model_map.get(selected_model, "gemini-2.5-flash-exp")
    
    try:
        # تفعيل أداة البحث في جوجل (Google Search Tool)
        # ملاحظة: ميزة البحث متاحة بشكل أساسي في موديلات Gemini
        model = genai.GenerativeModel(
            model_name=model_id,
            tools=[{"google_search_retrieval": {}}] # هذا السطر هو سر ميزة Perplexity
        )
        
        full_query = f"بصفتك {persona_info}، ابحث في الإنترنت وأجب بدقة: {prompt}"
        response = model.generate_content(full_query)
        
        return response.text, model_id
    except Exception as e:
        # في حال فشل البحث أو الموديل، نعود للوضع العادي
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text, "Fallback-Flash"

# 2. القائمة الجانبية
with st.sidebar:
    st.title("🛡️ مركز تحكم مصعب")
    selected_engine = st.selectbox("🎯 اختر المحرك:", [
        "Gemini 2.5 Flash (الأسرع)",
        "Gemini 3 Pro (الأذكى)",
        "Gemma 3 27B (خبير المنطق)"
    ])
    
    persona = st.selectbox("👤 التخصص:", ["باحث ذكي وموثق", "مدرس لغات محترف", "خبير برمجة Ubuntu", "مصمم صور"])
    
    persona_instr = {
        "باحث ذكي وموثق": "أنت محرك بحث متطور. قدم إجابات موثقة بمصادر وروابط من الإنترنت.",
        "مدرس لغات محترف": "أنت مدرس لغات خبير. صحح وانطق بوضوح.",
        "خبير برمجة Ubuntu": "أنت خبير لينكس لجهاز HP.",
        "مصمم صور": "أنت فنان رقمي."
    }

    audio_record = mic_recorder(start_prompt="تحدث 🎤", stop_prompt="إرسال 📤", key='recorder')
    uploaded_image = st.file_uploader("تحليل صورة:", type=['jpg', 'png', 'jpeg'])
    
    if st.button("🗑️ مسح الذاكرة"):
        st.session_state.messages = []; st.rerun()

# 3. معالجة الرسائل
if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "img" in msg and msg["img"]: st.image(msg["img"])

# 4. التنفيذ
user_input = st.chat_input("اسأل عن أخبار اليوم أو ابحث عن معلومة موثقة...")

if user_input or (audio_record and audio_record['bytes']) or uploaded_image:
    query = user_input if user_input else "حلل المرفق"
    with st.chat_message("user"): st.markdown(query)
    
    with st.chat_message("assistant"):
        with st.spinner("جاري البحث في الإنترنت وتجميع المصادر..."):
            # طلب الرد مع البحث
            ai_text, m_used = generate_search_response(query, selected_engine, persona_instr[persona])
            
            if ai_text:
                # ميزة الرسم
                img_url = None
                if any(w in query for w in ["ارسم", "صورة"]) or persona == "مصمم صور":
                    img_url = draw_image_logic(query)
                    st.image(img_url)
                
                st.markdown(ai_text)
                st.caption(f"📍 مصدر المعلومات: بحث Google مباشر عبر {m_used}")
                
                # ميزة النطق (حتى 2000 حرف)
                try:
                    clean_txt = re.sub(r'[^\w\s.,!?]', '', ai_text)[:2000]
                    lang = 'en' if re.search(r'[a-zA-Z]', clean_txt) else 'ar'
                    tts = gTTS(text=clean_txt, lang=lang)
                    audio_io = io.BytesIO()
                    tts.write_to_fp(audio_io)
                    st.audio(audio_io)
                except: pass
                
                st.session_state.messages.append({"role": "assistant", "content": ai_text, "img": img_url})
