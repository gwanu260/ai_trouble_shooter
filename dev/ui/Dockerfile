# 1. 기본 이미지
FROM python:3.12.0-slim

# 2. 작업디렉터리 -> 루트디렉토리가 설정됨
WORKDIR /app

# 3. requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
&& pip install --no-cache-dir -r requirements.txt

# 4. 코드복사 -> requirements.txt는 이미 복사되어 있음
COPY . .

# 5. 백그라운드(데몬)으로 서비스 가동 -> 컴포즈에서 대체되었음