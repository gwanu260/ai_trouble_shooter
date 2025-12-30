import os
from dotenv import load_dotenv
load_dotenv()

from langchain_aws import BedrockEmbeddings
from pinecone import Pinecone
from langchain_core.tools import tool


# --- RAG 검색용 Embedder ---
embedder = BedrockEmbeddings(
    model_id=os.getenv("BEDROCK_EMBEDDING_MODEL_ID"),
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

# --- Pinecone 연결 ---
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))
namespace = os.getenv("PINECONE_NAMESPACE", "dev")

def rag_search(query: str, top_k: int = 3) -> str:
    """
    RAG 검색 도구
    - query: 사용자 질문 또는 에러 시그니처
    - return: LLM 프롬프트에 바로 넣을 수 있는 문자열
    """
    qvec = embedder.embed_query(query)

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
@tool
def rag_search_tool(query: str, top_k: int = 5) -> str:
    """Pinecone에서 관련 지식을 검색해 반환한다."""
    return rag_search(query, top_k)