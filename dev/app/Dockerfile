FROM python:3.12.0-slim

WORKDIR /app
ENV PYTHONPATH=/app
# requirements.txt 경로 수정 (핵심)
COPY app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 나머지 코드 복사 (dev 전체가 들어옴)
COPY . . 