FROM python:3.12-slim

WORKDIR /app

# 루트 기준으로 경로 수정
COPY dev/ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 전체 복사
COPY . .

ENV PYTHONPATH=/app

# 실행 경로 수정
CMD ["streamlit", "run", "dev/ui/ui.py", "--server.address", "0.0.0.0", "--server.port", "8501"]