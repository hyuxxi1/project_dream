import streamlit as st
from openai import OpenAI
import re

# =========================================================
# 1. 페이지 초기 설정 및 세션 상태 초기화
# =========================================================
st.set_page_config(
    page_title="Solar Emotion Chatbot",
    page_icon="🌈",
    layout="wide" # 넓은 화면 사용
)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

if "current_theme" not in st.session_state:
    # 초기 테마: 중립 (어두운 회색 계열)
    st.session_state.current_theme = {
        "color_name": "중립",
        "bg_color": "#1E1E1E", # 매우 어두운 회색 배경
        "text_color": "#FFFFFF",
        "accent_color": "#FF4B4B" # 기본 포인트 색상
    }

# =========================================================
# 2. 동적 CSS 주입 함수 (감정에 따라 배경색 변경)
# =========================================================
def apply_dynamic_theme(theme):
    """
    세션 상태에 저장된 테마 정보를 바탕으로 
    Streamlit 앱 전체에 CSS를 동적으로 주입합니다.
    """
    bg_color = theme["bg_color"]
    text_color = theme["text_color"]
    accent_color = theme["accent_color"]

    # 은은한 Fade-in 효과를 위한 transition 추가
    st.markdown(f"""
        <style>
        /* 메인 앱 배경 */
        .stApp {{
            background-color: {bg_color};
            color: {text_color};
            transition: background-color 1.5s ease, color 1.5s ease;
        }}

        /* 채팅 메시지 컨테이너 스타일 정의 */
        .stChatMessage {{
            background-color: rgba(255, 255, 255, 0.05); /* 투명한 흰색 배경 */
            border-radius: 15px;
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        /* 포인트 색상 적용 (사이드바, 버튼 등) */
        h1, h2, h3, h4, h5, h6 {{
            color: {text_color} !important;
        }}
        
        .stButton>button {{
            background-color: {accent_color} !important;
            color: white !important;
            border: none !important;
        }}
        </style>
    """, unsafe_allow_html=True)

# 앱 시작 시 즉시 테마 적용
apply_dynamic_theme(st.session_state.current_theme)

# =========================================================
# 3. 사이드바 및 API 설정
# =========================================================
with st.sidebar:
    st.header("⚙️ 설정")
    # API 키 보안 처리
    api_key = st.secrets.get("UPSTAGE_API_KEY")
    if not api_key:
        api_key = st.text_input("Upstage API Key를 입력하세요:", type="password")
        if not api_key:
            st.info("API Key가 필요합니다.")
            st.stop()
    
    st.divider()
    # 현재 분석된 감정 상태 표시
    st.subheader("현재 내 감정 상태")
    st.info(f"🎨 **{st.session_state.current_theme['color_name']}**")
    
    if st.button("대화 초기화", use_container_width=True):
        st.session_state.messages = []
        # 초기 테마로 복구
        st.session_state.current_theme = {
            "color_name": "중립",
            "bg_color": "#1E1E1E",
            "text_color": "#FFFFFF",
            "accent_color": "#FF4B4B"
        }
        st.rerun()

client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")

# 메인 타이틀
st.markdown(f'<h1 style="text-align: center;">🌈 Solar 감정 적응형 챗봇</h1>', unsafe_allow_html=True)
st.caption(f'<p style="text-align: center;">내 기분에 따라 AI 비서의 말투와 배경색이 은은하게 변합니다.</p>', unsafe_allow_html=True)
st.divider()

# =========================================================
# 4. 이전 대화 출력
# =========================================================
for message in st.session_state.messages:
    # 시스템 메시지는 화면에 출력하지 않음
    if message["role"] == "system":
        continue
        
    avatar = "👤" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# =========================================================
# 5. 사용자 입력 및 테마/답변 생성
# =========================================================
prompt = st.chat_input("메시지를 입력하세요.")

if prompt:
    # 1) 사용자 메시지 기록 및 출력
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # 2) [핵심] Solar에게 감정 분석 요청 (비동기로 동시에 처리하면 더 좋지만, 여기서는 순차 처리)
    with st.spinner("내 감정을 분석 중..."):
        emotion_system_prompt = """
        당신은 세계 최고의 감정 분석가이자 테마 디자이너입니다. 
        사용자의 다음 입력을 분석하여 그 안에 담긴 핵심 감정 1가지를 정의하고, 
        그 감정을 은은하게 표현할 수 있는 어두운 계열의 배경색(Background Color, 16진수 HEX)과 
        그 배경에서 잘 보이는 텍스트 색상(Text Color)을 매칭하여 반환하세요.
        답변은 반드시 다음 형식을 지키세요: [감정이름, 배경색HEX, 텍스트색HEX]
        예: [기쁨, #2E4A3F, #FFFFFF] or [분노, #4A2E2E, #FFFFFF]
        배경색은 너무 밝지 않은 어두운 톤(Dark Tone)으로 설정하여 사용자의 눈을 보호하세요.
        """
        
        emotion_response = client.chat.completions.create(
            model="solar-pro", # 정확한 모델명으로 수정 필요
            messages=[
                {"role": "system", "content": emotion_system_prompt},
                {"role": "user", "content": f"입력: {prompt}"}
            ],
            temperature=0, # 일관된 분석을 위해 0으로 설정
        )
        
        emotion_data_raw = emotion_response.choices[0].message.content
        
        # 결과 파싱 (예: [기쁨, #2E4A3F, #FFFFFF] -> 기쁨, #2E4A3F, #FFFFFF)
        try:
            # 대괄호 및 공백 제거 후 쉼표로 분리
            emotion_data = emotion_data_raw.strip('[]').split(',')
            color_name = emotion_data[0].strip()
            bg_color = emotion_data[1].strip()
            text_color = emotion_data[2].strip()
            
            # 유효성 검사 (16진수 HEX 형식인지)
            hex_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
            if not hex_pattern.match(bg_color) or not hex_pattern.match(text_color):
                raise ValueError("Invalid HEX color")
            
            # 세션 상태에 새로운 테마 저장
            st.session_state.current_theme = {
                "color_name": color_name,
                "bg_color": bg_color,
                "text_color": text_color,
                "accent_color": text_color # 포인트 색상도 텍스트색과 동일하게
            }
            # 테마를 즉시 적용하기 위해 페이지 리런
            st.rerun()

        except Exception as e:
            # 파싱 실패 시 기본 테마 유지 (에러는 표시하지 않음)
            pass

    # 3) Solar에게 답변 생성 요청 (변경된 테마가 적용된 말투 유도)
    with st.chat_message("assistant", avatar="🤖"):
        
        # 현재 감정 상태를 System 프롬프트에 주입하여 말투 변경 유도
        current_color_name = st.session_state.current_theme["color_name"]
        
        if "messages" not in st.session_state or len(st.session_state.messages) == 0:
             final_messages = []
        else:
            final_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
        
        # 최상단에 테마 기반 시스템 프롬프트 삽입
        final_messages.insert(0, {
            "role": "system", 
            "content": f"당신은 현재 사용자가 '{current_color_name}'의 감정을 느끼고 있다고 판단하여, 이에 맞춘 분위기와 말투로 답변하는 유능한 AI 비서입니다."
        })

        # 답변 생성 (스트리밍)
        stream = client.chat.completions.create(
            model="solar-pro",
            messages=final_messages,
            stream=True
        )
        
        # 스트리밍 결과 출력
        response_text = st.write_stream(chunk.choices[0].delta.content for chunk in stream if chunk.choices and chunk.choices[0].delta.content)

    # 4) Assistant 응답 기록
    st.session_state.messages.append({"role": "assistant", "content": response_text})
