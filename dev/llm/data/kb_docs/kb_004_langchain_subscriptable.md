# 'AIMessage' object is not subscriptable (LangChain)

## 증상
- Python 에러:
  - `'AIMessage' object is not subscriptable`

## 대표 원인
- LangChain message 객체를 dict처럼 접근
  - 예: `msg["content"]` (X)
- 올바른 접근:
  - `msg.content` 또는 타입에 맞는 속성 사용

## 해결 방법
- message 타입 확인 (HumanMessage, AIMessage 등)
- content는 `.content`로 접근
- 리스트/딕셔너리 혼동하지 않기

## 재발 방지
- 타입힌트 및 mypy
- 메시지 출력 시 `type(msg)`를 로깅

## 시그니처
- signature: `LANGCHAIN:AIMessage not subscriptable`
- tags: langchain, messages
