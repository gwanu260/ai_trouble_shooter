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
    mode_switch = st.toggle("시니어")  # 기본 주니어

# ---------- Sidebar ---------- #
with st.sidebar:
    st.title("⚙️ 설정")
    level = st.selectbox("모드", ["주니어", "시니어"], index=(1 if mode_switch else 0))
    language = st.selectbox("언어", ["auto", "python", "C", "javascript"], index=0)

st.markdown("---")

# ---------- Input Area ---------- #
st.markdown("#### 🧩 분석 입력")

input_log = st.text_area("🐞 에러 로그 입력", height=150)

with st.expander("💡 코드 스니펫 (선택 입력)", expanded=False):
    input_code = st.text_area("코드 / 발췌 내용", height=150)

# 분석 실행 버튼 센터 정렬
_, center_btn, _ = st.columns([4, 2, 4])
with center_btn:
    analyze_clicked = st.button("🔍 분석하기", use_container_width=True)

st.markdown("---")

# ---------- Results ---------- #
if analyze_clicked:
    if not input_log.strip():
        st.warning("에러 로그를 입력해주세요!")
    else:
        with st.spinner("분석 중… ⏳"):
            payload = {
                "error_log": input_log,
                "code_snippet": input_code if input_code else None
            }
            response = requests.post(API_URL, json=payload)

        if response.status_code != 200:
            st.error("❌ FastAPI 서버에 문제가 있습니다. 연결을 확인하세요.")
        else:
            result = response.json()
            st.success("🎯 분석 완료!")

            col_cause, col_solution, col_prevent = st.columns(3)

            with col_cause:
                st.markdown("### 🔴 원인")
                st.write(result.get("cause", "정보 없음"))

            with col_solution:
                st.markdown("### 🔵 해결")
                st.write(result.get("solution", "해결 가이드 없음"))

            with col_prevent:
                st.markdown("### 🟢 재발 방지")
                st.write(result.get("prevention", "데이터 부족"))
