# Chunking 전략 가이드 (로그/코드/RUNBOOK)

## 목표
- 검색 품질과 답변 근거성을 높이기 위해 문서를 적절히 분할

## 추천 전략
1) Markdown 헤더 기반 분할
2) 코드블록 단위 보존
3) 토큰 기반 fallback (chunk_size/overlap)

## 권장 파라미터
- chunk_size: 400~800 tokens (또는 1500~3000 chars)
- overlap: 10~20%

## 재발 방지
- 너무 작은 chunk는 문맥 손실
- 너무 큰 chunk는 검색이 뭉개짐

## 시그니처
- signature: `RAG:chunking strategy`
- tags: rag, chunking, retrieval
