# Pinecone Dimension mismatch

## 증상
- Pinecone upsert/query 시 에러:
  - dimension mismatch
  - invalid vector size

## 대표 원인
- 인덱스 dimension과 임베딩 모델 출력 차원이 불일치

## 해결 방법
- 임베딩 모델 차원 확인 후 인덱스 재생성
- 같은 인덱스에 서로 다른 임베딩 모델 섞지 않기

## 재발 방지
- 앱 시작 시 preflight: embedder.dim == index.dim 검사
- namespace로 버전 분리 (v1, v2)

## 시그니처
- signature: `PINECONE:dimension mismatch`
- tags: pinecone, embedding, vector_db
