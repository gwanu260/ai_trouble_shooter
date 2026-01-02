# 1. Python 베이스 이미지
FROM python:3.12-slim

# 2. 작업 디렉토리
WORKDIR /app

# 3. requirements 먼저 복사 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. UI 코드 복사
COPY ui/app.py .

# 5. Streamlit 포트
EXPOSE 8501

# 6. Streamlit 실행
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]