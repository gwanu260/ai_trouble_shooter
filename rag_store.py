from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings
import boto3
import os, glob, hashlib
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

load_dotenv()

# 1) Embedder

embedder = BedrockEmbeddings(model_id=os.getenv('BEDROCK_EMBEDDING_MODEL_ID'),
                            region_name=os.getenv('AWS_REGION'),
                            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

# 2) Splitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,      # 대략 400~800 tokens 수준(경험치)
    chunk_overlap=200
)

# 3) Pinecone init

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX"))
namespace = os.getenv("PINECONE_NAMESPACE", "dev")


def load_md_docs(folder="data/kb_docs"):
    paths = sorted(glob.glob(os.path.join(folder, "*.md")))
    docs = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            docs.append((p, f.read()))
    return docs

def make_id(source: str, chunk_index: int, text: str) -> str:
    # 중복방지: 같은 내용이면 같은 id로 업서트(갱신)
    h = hashlib.sha1(f"{source}|{chunk_index}|{text}".encode("utf-8")).hexdigest()
    return h

def main():
    docs = load_md_docs("data/kb_docs")
    print(f"[load] docs={len(docs)}")

    upserts = []
    total_chunks = 0

    for source, doc_text in docs:
        chunks = splitter.split_text(doc_text)
        total_chunks += len(chunks)

        vectors = embedder.embed_documents(chunks)  # List[List[float]]

        for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
            _id = make_id(source, i, chunk)
            metadata = {
                "source": source,
                "chunk_index": i,
                # 너무 길면 잘라서 넣어(메타데이터 과다 방지)
                "text": chunk[:1500],
                "doc_type": "kb_md",
            }
            upserts.append((_id, vec, metadata))

        # 너무 많이 쌓이면 배치 업서트
        if len(upserts) >= 100:
            index.upsert(vectors=upserts, namespace=namespace)
            print(f"[upsert] +{len(upserts)}")
            upserts.clear()

    # 남은 것 업서트
    if upserts:
        index.upsert(vectors=upserts, namespace=namespace)
        print(f"[upsert] +{len(upserts)}")

    print(f"[done] total_chunks={total_chunks}")

if __name__ == "__main__":
    main()