import sys
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import re
import uuid
from dotenv import load_dotenv

# [추가] 가역적 마스킹 매니저 임포트
from dev.app.masking import MaskingManager

# 환경 변수 로드 (최우선 실행)
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
        
        # [1] 마스킹 매니저 인스턴스 생성
        masker = MaskingManager()
        
        # [2] 입력 데이터 정제 및 마스킹 (400 에러 방지 핵심)
        # .strip()으로 보이지 않는 공백을 제거하고, 빈 값일 경우 "None" 텍스트를 넣어 공백 발생을 차단합니다.
        log_content = req.error_log.strip() if req.error_log and req.error_log.strip() else "No log content provided"
        code_content = req.code.strip() if req.code and req.code.strip() else "No code content provided"
        
        masked_log = masker.mask(log_content).strip()
        masked_code = masker.mask(code_content).strip()
        
        initial_state = {
            "messages": [], 
            "persona": req.persona,
            "input_mode": req.input_mode,
            "log_text": masked_log,   # 마스킹된 로그 전달
            "code_text": masked_code  # 마스킹된 코드 전달
        }
        
        # [3] LLM 호출 (마스킹된 상태로 분석 진행)
        final_state = app_graph.invoke(initial_state)
        raw_text = final_state["messages"][-1].content.strip()

        # [4] 응답 데이터 추출 및 언마스킹 로직 통합
        def robust_extract_and_unmask(field, text):
            # JSON 내의 필드를 찾기 위한 정규식
            pattern = rf'"{field}"\s*:\s*"(.*?)"(?=\s*,\s*"|\s*}}\s*$|\s*}}?\s*```|$)'
            m = re.search(pattern, text, re.DOTALL)
            if m: 
                # 추출된 값에서 이스케이프된 줄바꿈 등을 처리
                val = m.group(1).replace('\\n', '\n').replace('\\"', '"').strip()
                # [핵심] 추출된 결과에서 IP_ADDR_0 등을 실제 IP로 복구
                return masker.unmask(val)
            return f"{field} 분석 완료 (상세 내용 없음)"

        # 각 필드에 대해 추출과 동시에 언마스킹 수행
        cause_final = robust_extract_and_unmask("cause", raw_text)
        sol_final = robust_extract_and_unmask("solution", raw_text)
        prev_final = robust_extract_and_unmask("prevention", raw_text)

        return {
            "cause": cause_final,
            "solution": sol_final,
            "prevention": prev_final
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