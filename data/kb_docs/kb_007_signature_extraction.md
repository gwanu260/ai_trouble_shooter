# Error signature 추출 가이드

## 목적
- 에러 로그의 “핵심 패턴”을 뽑아 RAG 검색의 키로 사용

## 규칙 예시
- Exception 타입 + 핵심 메시지
- 상위 1~3줄의 Traceback 핵심 라인
- HTTP 상태코드 + 엔드포인트(가능하면)

## 예시
- `ValidationException:model identifier invalid`
- `FASTAPI:422 validation error`
- `LANGCHAIN:AIMessage not subscriptable`

## 재발 방지
- request_id/timestamp 같은 변동값은 제거(마스킹)

## 시그니처
- signature: `RAG:signature extraction`
- tags: rag, signature, parsing
