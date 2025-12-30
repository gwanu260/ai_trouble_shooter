# 구조
my-web-service/
├── api.py           # FastAPI 서버 코드
├── ui.py            # Streamlit 앱 코드
├── tests/
│   ├── test_api.py  # 백엔드 테스트
│   └── test_ui.py   # 프론트엔드 테스트
├── requirements.txt
└── .github/
    └── workflows/
        └── web-ci.yml

# 실행
- front   : streamlit run ui.py
- backend : uvicorn api:app --reload