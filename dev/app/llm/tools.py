"""
tools.py

LangGraph Agent에서 사용하는 외부 Tool 정의 모듈.

이 파일은 LLM이 직접 호출할 수 있는 Tool과,
그 Tool이 내부적으로 사용하는 실제 구현 함수를 포함한다.

현재 포함된 Tool:
- rag_search:
    Pinecone 벡터 DB를 사용해
    에러 로그 / 코드 / 질문과 관련된 지식(KB)을 검색한다.

역할 분리 원칙:
- Agent(LLM)는 '언제 검색할지'만 판단한다.
- tools.py는 '어떻게 검색할지'만 책임진다.
"""
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_aws import BedrockEmbeddings
from pinecone import Pinecone
from langchain_core.tools import tool
from typing import Optional

_embedder: Optional[BedrockEmbeddings] = None
_pinecone_index = None
_namespace: Optional[str] = None

def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it in your .env or CI secrets before using rag_search."
        )
    return v

def get_embedder() -> BedrockEmbeddings:
    global _embedder
    if _embedder is not None:
        return _embedder

    model_id = _require_env("BEDROCK_EMBEDDING_MODEL_ID")
    region = _require_env("AWS_REGION")

    _embedder = BedrockEmbeddings(
        model_id=model_id,
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    return _embedder


def get_pinecone_index():
    global _pinecone_index, _namespace
    if _pinecone_index is not None:
        return _pinecone_index

    api_key = _require_env("PINECONE_API_KEY")
    index_name = _require_env("PINECONE_INDEX")
    _namespace = os.getenv("PINECONE_NAMESPACE", "dev")

    pc = Pinecone(api_key=api_key)
    _pinecone_index = pc.Index(index_name)
    return _pinecone_index

def rag_search(query: str, top_k: int = 3) -> str:
    """
    RAG 검색 도구
    - query: 사용자 질문 또는 에러 시그니처
    - return: LLM 프롬프트에 바로 넣을 수 있는 문자열
    """
    embedder = get_embedder()
    index = get_pinecone_index()
    qvec = embedder.embed_query(query)
    namespace = _namespace or "dev"

    res = index.query(
        vector=qvec,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True,
    )

    chunks = []
    for m in res["matches"]:
        md = m.get("metadata", {}) or {}
        chunks.append(
            f"- ({m['score']:.3f}) {md.get('source','?')}#{md.get('chunk_index','?')}\n"
            f"{md.get('text','')}"
        )

    return "\n\n".join(chunks)
# =====================================================
# 2) LangGraph / Agent용 Tool 래퍼
# =====================================================
@tool("rag_search")
def rag_search_tool(query: str) -> str:
    """
    에러 로그, 코드, 질문을 기반으로
    Pinecone 벡터 DB에서 관련 트러블슈팅 지식을 검색한다.
    """
    print("[TOOL CALLED] rag_search:", query[:80])
    return rag_search(query, top_k=5)