import sys
import os
import re
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
from dotenv import load_dotenv

# 가역적 마스킹 매니저 임포트
from dev.app.masking import MaskingManager

# 환경 변수 로드
load_dotenv()

# 경로 자동 인식 로직
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    from dev.app.llm.agent_with_graph import app as app_graph
    from dev.app.llm.tools import get_embedder, get_pinecone_index
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
        
        masker = MaskingManager()
        
        # 1. 입력 데이터 정제 및 마스킹
        log_content = req.error_log.strip() if req.error_log and req.error_log.strip() else "No log content provided"
        code_content = req.code.strip() if req.code and req.code.strip() else "No code content provided"
        
        masked_log = masker.mask(log_content).strip()
        masked_code = masker.mask(code_content).strip()

        # ==========================================================
        # [수정 부분] 보안 확인을 위한 터미널 출력 로그 추가
        # 실제 IP가 아닌 [IP_ADDR_0] 형태로 출력되는지 확인할 수 있습니다.
        # ==========================================================
        print("\n" + "="*50)
        print("🔒 [보안 확인] LLM으로 전송되는 마스킹된 데이터")
        print(f"📡 Masked Log: {masked_log[:200]}{'...' if len(masked_log) > 200 else ''}")
        print(f"💻 Masked Code: {masked_code[:200]}{'...' if len(masked_code) > 200 else ''}")
        print("="*50 + "\n")
        # ==========================================================
        
        initial_state = {
            "messages": [], 
            "persona": req.persona,
            "input_mode": req.input_mode,
            "log_text": masked_log,
            "code_text": masked_code
        }
        
        # 2. LLM 호출
        final_state = app_graph.invoke(initial_state)
        raw_text = final_state["messages"][-1].content.strip()

        # 3. 강화된 추출 로직 및 언마스킹 수행
        def robust_extract_and_unmask(field, text):
            patterns = [
                rf'"{field}"\s*:\s*"(.*?)"(?=\s*,\s*"|\s*}}\s*$|\s*}}?\s*```|$)',
                rf'"{field}"\s*:\s*(.*?)(?=\n\s*"\w+"|$)',
                rf'\*\*{field}\*\*[:\s]+(.*?)(?=\n\*\*|$)',
                rf'{field}[:\s]+(.*?)(?=\n\w+[:\s]|$)'
            ]
            
            extracted = None
            for pattern in patterns:
                m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if m:
                    extracted = m.group(1).strip()
                    break
            
            if extracted:
                clean_text = extracted.strip('"').replace('\\n', '\n').replace('\\"', '"').strip()
                # 여기서 마스킹 해제(복구)가 일어납니다.
                return masker.unmask(clean_text)
            
            return f"{field} 분석 정보 추출 실패"

        return {
            "cause": robust_extract_and_unmask("cause", raw_text),
            "solution": robust_extract_and_unmask("solution", raw_text),
            "prevention": robust_extract_and_unmask("prevention", raw_text)
        }

    except Exception as e:
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