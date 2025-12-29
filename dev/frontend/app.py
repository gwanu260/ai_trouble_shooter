import streamlit as st
import requests

API_URL = "http://localhost:8000/analyze/log"

st.title("AI Trouble Shooter")

log_input = st.text_area("에러 로그를 입력하세요:")

if st.button("분석하기"):
    if not log_input.strip():
        st.warning("에러 로그를 입력해주세요!")
    else:
        with st.spinner("분석 중..."):
            payload = {"log": log_input}
            response = requests.post(API_URL, json=payload)

            if response.status_code == 200:
                result = response.json()
                st.subheader("분석 결과")
                st.json(result)
            else:
                st.error("서버 에러! FastAPI 상태를 확인해주세요.")