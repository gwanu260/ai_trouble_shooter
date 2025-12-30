# Streamlit session_state 사용 패턴

## 증상
- 버튼 클릭할 때마다 결과가 사라지거나 UI가 초기화됨

## 대표 원인
- Streamlit은 interaction마다 스크립트를 재실행함
- 상태 유지 없으면 결과가 리셋됨

## 해결 방법
- `st.session_state`에 결과 저장
- “분석하기” 버튼 눌렀을 때만 호출되도록 guard 추가

## 재발 방지
- 결과 출력과 호출 로직 분리
- API 응답을 세션에 캐싱

## 시그니처
- signature: `STREAMLIT:session_state reset`
- tags: streamlit, ui, state
