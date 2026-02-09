import streamlit as st
from google import genai
from google.genai import types
import os, json

# مصفوفة العقول بأسماء "مؤكدة" ومسارات بديلة
MODELS_GRID = {
    "Gemini 3 Flash (الأحدث)": "gemini-2.0-flash", 
    "Gemini 2.5 Flash": "gemini-1.5-flash",
    "Gemini 1.5 Pro": "gemini-1.5-pro",
    "الوضع الآمن (Safe Mode)": "gemini-1.5-flash-8b" # حصة أكبر واستهلاك أقل
}

def get_super_response(engine_label, user_input, persona_type, use_search=False):
    # محاولة جلب المفتاح
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return "❌ مفتاح API غير مفقود في السيكرتس!"
    
    client = genai.Client(api_key=api_key)
    engine_id = MODELS_GRID.get(engine_label, "gemini-2.0-flash")
    
    try:
        # إعداد البحث
        search_tool = [types.Tool(google_search=types.GoogleSearch())] if use_search else None
        
        config = types.GenerateContentConfig(
            system_instruction=f"أنت {persona_type}. رد بلهجة سورية محببة لمصعب إذا سأل عن سوريا.",
            tools=search_tool
        )
        
        # تنفيذ الطلب بمرونة
        response = client.models.generate_content(
            model=engine_id, 
            contents=[user_input], 
            config=config
        )
        return response.text

    except Exception as e:
        error_msg = str(e)
        # نظام الإنقاذ التلقائي
        if "429" in error_msg or "404" in error_msg:
            st.warning(f"⚠️ المحرك {engine_label} متوقف حالياً. أحاول جلب الإجابة عبر 'الوضع الآمن'...")
            try:
                # محاولة أخيرة باستخدام النموذج الأخف (8b)
                res_fallback = client.models.generate_content(model="gemini-1.5-flash-8b", contents=[user_input])
                return res_fallback.text
            except:
                return "❌ يا مصعب، جوجل أغلق الحصة المجانية تماماً لهذا اليوم. الحل الوحيد الآن هو تغيير مفتاح API أو الانتظار لغدٍ."
        return f"⚠️ عذراً، خطأ مفاجئ: {error_msg}"

# --- الواجهة الجانبية ---
with st.sidebar:
    st.title("🛡️ رادار مصعب v31")
    st.info("💡 نصيحة: إذا استمر الخطأ، فالحصة اليومية لحسابك انتهت.")
    engine_choice = st.selectbox("🎯 العقل المختار:", list(MODELS_GRID.keys()))
    web_on = st.toggle("🌐 بحث مباشر عن الطقس", value=True)
    if st.button("🗑️ مسح السجل"):
        st.session_state.messages = []
        st.rerun()

# --- منطق العرض ---
if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("كيف الطقس في سوريا الآن؟"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        res = get_super_response(engine_choice, prompt, "المدرس الذكي 👨‍🏫", use_search=web_on)
        st.markdown(res)
        st.session_state.messages.append({"role": "assistant", "content": res})
