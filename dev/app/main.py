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

        # 3. [강화된 추출 로직] 상세 내용을 끝까지 긁어오고 동시에 언마스킹 수행
        def robust_extract_and_unmask(field, text):
            # JSON 스타일 ("field": "value") 뿐만 아니라 마크다운 스타일까지 모두 대응하는 패턴 리스트
            patterns = [
                rf'"{field}"\s*:\s*"(.*?)"(?=\s*,\s*"|\s*}}\s*$|\s*}}?\s*```|$)', # 표준 JSON
                rf'"{field}"\s*:\s*(.*?)(?=\n\s*"\w+"|$)', # 따옴표가 없는 값
                rf'\*\*{field}\*\*[:\s]+(.*?)(?=\n\*\*|$)', # 마크다운 (**cause**: 내용)
                rf'{field}[:\s]+(.*?)(?=\n\w+[:\s]|$)' # 일반 텍스트 (cause: 내용)
            ]
            
            extracted = None
            for pattern in patterns:
                m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if m:
                    extracted = m.group(1).strip()
                    break
            
            if extracted:
                # 불필요한 따옴표, 이스케이프 제거 및 언마스킹
                clean_text = extracted.strip('"').replace('\\n', '\n').replace('\\"', '"').strip()
                return masker.unmask(clean_text)
            
            # 최후의 수단: 문자열 인덱스로 직접 찾기
            try:
                search_key = f'"{field}"'
                if search_key in text:
                    start_idx = text.find(search_key) + len(search_key)
                    # 콜론(:)과 따옴표(") 건너뛰기
                    after_key = text[start_idx:].lstrip(' :\"')
                    # 다음 필드 구분자( ", )나 종료 기호( "} ) 전까지 잘라냄
                    end_pos = re.search(r'["\s]*[,}]', after_key)
                    if end_pos:
                        return masker.unmask(after_key[:end_pos.start()].strip())
            except:
                pass

            return f"{field} 분석 정보 추출 실패 (LLM 응답 형식 확인 필요)"

        # 각 필드별로 데이터 추출 실행
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