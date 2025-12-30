import streamlit as st
import requests

st.title("Item 찾기")

item_id = st.number_input("Item ID 입력", min_value=1, step=1)

if st.button("Search"):
    try:
        # 실제 환경에서는 localhost가 아닌 배포된 API 주소를 사용해야 함
        response = requests.get(f"http://localhost:8000/items/{item_id}")
        if response.status_code == 200:
            data = response.json()
            st.success(f"Found: {data['name']}")
        else:
            st.error("Item not found")
    except Exception as e:
        st.error(f"Connection Error: {e}")