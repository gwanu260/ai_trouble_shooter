# 1. 기본 이미지
FROM python:3.12.0-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 루트 기준으로 의존성 파일 복사 및 설치
# 빌드 컨텍스트가 루트이므로 dev/app/ 경로를 명시합니다.
COPY dev/app/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 4. 프로젝트 전체 코드 복사 (dev/llm 모듈 참조를 위해 필수)
COPY . .

# 5. 환경 변수 설정: /app을 파이썬 모듈 검색 경로에 추가
ENV PYTHONPATH=/app

# 6. 실행 명령: 모듈 경로를 포함하여 실행
CMD ["uvicorn", "dev.app.main:app", "--host", "0.0.0.0", "--port", "8000"]