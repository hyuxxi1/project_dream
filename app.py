import io
import streamlit as st
from openai import OpenAI
from gtts import gTTS

# =========================================================
# 1. 페이지 설정 & 커스텀 CSS
# =========================================================
st.set_page_config(
    page_title="Solar AI Assistant with Voice",
    page_icon="🎙️",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    .gradient-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF4B4B, #FF8F8F);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="gradient-title">🎙️ Upstage Solar Voice Chatbot</h1>', unsafe_allow_html=True)
st.caption("Solar LLM 답변을 실시간 음성(TTS)으로 들어보세요.")

# =========================================================
# 2. TTS 음성 변환 함수 (BytesIO 활용)
# =========================================================
def create_tts_audio(text: str, lang: str = "ko") -> io.BytesIO:
    """텍스트를 gTTS를 이용해 mp3 음성 데이터 바이트 스트림으로 변환합니다."""
    # Markdown 기호 및 특수문자 일부 정제 (음성 출력 품질 향상)
    clean_text = text.replace("*", "").replace("#", "").replace("`", "").strip()
    
    tts = gTTS(text=clean_text, lang=lang)
    audio_buffer = io.BytesIO()
    tts.write_to_fp(audio_buffer)
    audio_buffer.seek(0)
    return audio_buffer

# =========================================================
# 3. 사이드바 (설정 & TTS 옵션)
# =========================================================
with st.sidebar:
    st.header("⚙️ 설정 (Control Panel)")
    
    # 3-1. API Key 입력
    api_key = st.secrets.get("UPSTAGE_API_KEY")
    if not api_key:
        api_key = st.text_input("Upstage API Key:", type="password")
        if not api_key:
            st.warning("🔑 API Key를 입력하세요.")
            st.stop()
            
    st.divider()
    
    # 3-2. TTS 음성 기능 설정
    st.subheader("🔊 음성(TTS) 설정")
    enable_tts = st.toggle("음성 답변 플레이어 생성", value=True)
    auto_play = st.checkbox("답변 생성 시 자동 재생", value=False)
    tts_lang = st.selectbox("음성 언어", ["한국어 (ko)", "영어 (en)"], index=0)
    lang_code = "ko" if "한국어" in tts_lang else "en"
    
    st.divider()
    
    # 3-3. 대화 초기화
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.audio_store = {}
        st.rerun()

# OpenAI 클라이언트 및 세션 초기화
client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "audio_store" not in st.session_state:
    st.session_state.audio_store = {}  # 메시지 인덱스별 오디오 데이터 저장

# =========================================================
# 4. 이전 대화 및 저장된 음성 출력
# =========================================================
for idx, message in enumerate(st.session_state.messages):
    avatar = "👤" if message["role"] == "user" else "⚡"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        
        # 이전 Assistant 답변의 음성 플레이어 유지
        if message["role"] == "assistant" and enable_tts:
            if idx in st.session_state.audio_store:
                st.audio(st.session_state.audio_store[idx], format="audio/mp3")

# =========================================================
# 5. 사용자 입력 및 답변 생성 + TTS 처리
# =========================================================
user_prompt = st.chat_input("메시지를 입력하세요...")

if user_prompt:
    # 1) 사용자 메시지 기록 및 출력
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_prompt)

    # 2) Assistant 응답 생성 (스트리밍)
    with st.chat_message("assistant", avatar="⚡"):
        stream = client.chat.completions.create(
            model="solar-pro",
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            stream=True
        )

        def generate_response():
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        response_text = st.write_stream(generate_response())

        # 3) TTS 음성 생성 및 오디오 플레이어 출력
        if enable_tts and response_text:
            with st.spinner("🔊 음성을 생성하는 중..."):
                audio_data = create_tts_audio(response_text, lang=lang_code)
                new_msg_idx = len(st.session_state.messages)  # 저장될 메시지의 인덱스
                
                # 세션에 오디오 바이너리 저장 (새로고침 시에도 유지)
                st.session_state.audio_store[new_msg_idx] = audio_data.getvalue()
                
                # 플레이어 출력
                st.audio(audio_data, format="audio/mp3", autoplay=auto_play)

    # 4) Assistant 메시지 기록
    st.session_state.messages.append({"role": "assistant", "content": response_text})
