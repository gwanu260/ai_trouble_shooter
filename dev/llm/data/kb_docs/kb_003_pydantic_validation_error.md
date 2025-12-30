# Pydantic ValidationError (FastAPI Request Body)

## 증상
- FastAPI에서 422 Unprocessable Entity
- 또는 Pydantic ValidationError

## 대표 원인
1) 필드 타입 불일치 (str로 오는데 int 기대)
2) required 필드 누락
3) nested schema 구조 mismatch

## 해결 방법
- request/response schema를 프론트와 합의 (DTO 명세)
- Optional 필드와 기본값 처리
- payload 예시를 swagger에 고정

## 재발 방지
- contract test 작성
- 프론트에서 전송 전 payload validate

## 시그니처
- signature: `FASTAPI:422 validation error`
- tags: fastapi, pydantic, schema
