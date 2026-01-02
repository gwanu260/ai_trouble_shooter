import sys
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import re
import uuid
from dotenv import load_dotenv

# 환경 변수 로드 (최우선 실행)
load_dotenv()

# 경로 자동 인식 로직
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from dev.llm.agent_with_graph import app as app_graph
    from dev.llm.tools import get_embedder, get_pinecone_index
except ImportError as e:
    print(f"❌ Import Error: {e}")
    raise

app = FastAPI()

class AnalyzeRequest(BaseModel):
    persona: Literal["junior", "senior"]
    input_mode: Literal["log", "code", "log_code"]
    error_log: Optional[str] = ""
    code: Optional[str] = ""

class AnalyzeResponse(BaseModel):
    cause: str
    solution: str
    prevention: str

class SaveRequest(BaseModel):
    persona: str
    error_log: str
    code: str
    cause: str
    solution: str

@app.post("/analyze/log", response_model=AnalyzeResponse)
async def analyze_log(req: AnalyzeRequest):
    try:
        print(f"🚀 분석 요청 수신: {req.input_mode} 모드")
        
        initial_state = {
            "messages": [], 
            "persona": req.persona,
            "input_mode": req.input_mode,
            "log_text": req.error_log,
            "code_text": req.code
        }
        
        # 이 지점에서 에러가 날 확률이 높음 (LLM 호출)
        final_state = app_graph.invoke(initial_state)
        raw_text = final_state["messages"][-1].content

        def robust_extract(field, text):
            pattern = rf'"{field}"\s*:\s*"(.*?)"(?=\s*,\s*"|\s*}}\s*$|\s*}}?\s*```|$)'
            m = re.search(pattern, text, re.DOTALL)
            if m: return m.group(1).replace('\\n', '\n').replace('\\"', '"').strip()
            return None

        return {
            "cause": robust_extract("cause", raw_text) or "분석 완료",
            "solution": robust_extract("solution", raw_text) or "해결책 생성 완료",
            "prevention": robust_extract("prevention", raw_text) or "가이드 생성 완료"
        }
    except Exception as e:
        # 터미널에 상세 에러 출력
        print(f"❌ [Server Error] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save/result")
async def save_result(req: SaveRequest):
    try:
        embedder = get_embedder()
        index = get_pinecone_index()
        target_namespace = os.getenv("PINECONE_NAMESPACE", "dev")

        combined_text = f"Log: {req.error_log}\nCode: {req.code}"
        vector = embedder.embed_query(combined_text)
        
        metadata = {
            "persona": req.persona,
            "cause": req.cause[:500],
            "solution": req.solution[:500],
            "doc_type": "user_contribution"
        }
        
        index.upsert(vectors=[(str(uuid.uuid4()), vector, metadata)], namespace=target_namespace)
        return {"status": "success", "message": "저장 완료"}
    except Exception as e:
        print(f"❌ [Save Error] {str(e)}")
        raise HTTPException(status_code=500, detail=f"저장 실패: {str(e)}")