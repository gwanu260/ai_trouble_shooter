import streamlit as st
import requests

API_URL = "http://localhost:8000/analyze/log"

# 페이지 레이아웃 세팅
st.set_page_config(page_title="🔍 AI Trouble Shooter", layout="wide")

# ---------- Header ---------- #
col_title, col_mode = st.columns([8, 2])
with col_title:
    st.markdown("## 🔍 AI Trouble Shooter — Code Analyzer")
with col_mode:
    # 1. 시니어/주니어 토글 스위치
    mode_switch = st.toggle("시니어 모드", value=False)

# ---------- Sidebar ---------- #
with st.sidebar:
    st.title("⚙️ 설정")
    # 토글 스위치와 연동된 셀렉트 박스
    level = st.selectbox(
        "사용자 레벨", 
        ["주니어", "시니어"], 
        index=(1 if mode_switch else 0),
        help="분석 결과의 깊이를 조절합니다."
    )
    language = st.selectbox("언어", ["auto", "python", "C", "javascript"], index=0)

st.markdown("---")

# ---------- Input Area (양옆 배치) ---------- #
st.markdown("#### 🧩 분석 입력")

# 2. columns를 사용하여 입력창을 양옆으로 배치
col_log, col_code = st.columns(2)

with col_log:
    input_log = st.text_area(
        "🐞 에러 로그 입력 (선택)", 
        height=250, 
        placeholder="에러 트레이스백을 입력하세요..."
    )

with col_code:
    input_code = st.text_area(
        "💡 코드 스니펫 입력 (선택)", 
        height=250, 
        placeholder="관련 소스 코드를 입력하세요..."
    )

# 분석 실행 버튼 센터 정렬
_, center_btn, _ = st.columns([4, 2, 4])
with center_btn:
    analyze_clicked = st.button("🔍 분석하기", use_container_width=True)

st.markdown("---")

# ---------- Results ---------- #
if analyze_clicked:
    if not input_log.strip() and not input_code.strip():
        st.error("❗ 에러 로그나 코드 스니펫 중 적어도 하나는 입력해야 합니다.")
    else:
        with st.spinner("분석 중… ⏳"):
            # 입력 상태에 따른 모드 결정
            if input_log.strip() and input_code.strip():
                mode = "log_code"
            elif input_code.strip():
                mode = "code"
            else:
                mode = "log"

            # 3. 최종 결정된 페르소나 값 (영문으로 변환하여 백엔드 전달)
            persona_val = "senior" if level == "시니어" else "junior"

            payload = {
                "persona": persona_val,
                "input_mode": mode,
                "error_log": input_log,
                "code": input_code
            }
            
            try:
                response = requests.post(API_URL, json=payload)
                
                if response.status_code != 200:
                    st.error("❌ FastAPI 서버에 문제가 있습니다. 연결을 확인하세요.")
                else:
                    result = response.json()
                    st.success(f"🎯 {level} 모드 분석 완료!")

                    # 결과 레이아웃
                    col_cause, col_solution, col_prevent = st.columns(3)

                    with col_cause:
                        st.markdown("### 🔴 원인")
                        st.info(result.get("cause", "정보 없음"))

                    with col_solution:
                        st.markdown("### 🔵 해결")
                        st.success(result.get("solution", "해결 가이드 없음"))

                    with col_prevent:
                        st.markdown("### 🟢 재발 방지")
                        st.warning(result.get("prevention", "데이터 부족"))
            except Exception as e:
                st.error(f"서버 연결 오류: {str(e)}")