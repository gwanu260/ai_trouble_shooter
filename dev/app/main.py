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
        
        # [2] 입력 데이터 마스킹 및 공백 제거 (Anthropic 400 에러 방지 핵심)
        # .strip()을 사용하여 텍스트 끝에 남은 보이지 않는 공백을 제거합니다.
        log_content = req.error_log.strip() if req.error_log else ""
        code_content = req.code.strip() if req.code else ""
        
        masked_log = masker.mask(log_content)
        masked_code = masker.mask(code_content)
        
        initial_state = {
            "messages": [], 
            "persona": req.persona,
            "input_mode": req.input_mode,
            "log_text": masked_log,   # 마스킹된 로그 전달
            "code_text": masked_code  # 마스킹된 코드 전달
        }
        
        # [3] LLM 호출 (마스킹된 상태로 분석 진행)
        final_state = app_graph.invoke(initial_state)
        # LLM 응답 자체의 앞뒤 공백도 미리 제거합니다.
        raw_text = final_state["messages"][-1].content.strip()

        def robust_extract(field, text):
            # 정규표현식으로 JSON 형태의 필드 추출
            pattern = rf'"{field}"\s*:\s*"(.*?)"(?=\s*,\s*"|\s*}}\s*$|\s*}}?\s*```|$)'
            m = re.search(pattern, text, re.DOTALL)
            if m: 
                # 줄바꿈 및 따옴표 이스케이프 처리 후 앞뒤 공백 제거
                extracted = m.group(1).replace('\\n', '\n').replace('\\"', '"')
                return extracted.strip()
            return None

        # [4] 응답 데이터 복구 (언마스킹)
        # 추출된 원시 답변들을 가져옵니다.
        cause_raw = robust_extract("cause", raw_text) or "분석 완료"
        sol_raw = robust_extract("solution", raw_text) or "해결책 생성 완료"
        prev_raw = robust_extract("prevention", raw_text) or "가이드 생성 완료"

        # 마스킹 테이블을 이용해 실제 IP 등으로 복구하여 반환
        return {
            "cause": masker.unmask(cause_raw),
            "solution": masker.unmask(sol_raw),
            "prevention": masker.unmask(prev_raw)
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