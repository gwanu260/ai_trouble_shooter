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
        
        # 1. 입력 정제 및 400 에러 방지 (None 텍스트 할당)
        raw_log = (req.error_log or "").strip()
        raw_code = (req.code or "").strip()
        
        log_content = raw_log if raw_log else "No log content provided"
        code_content = raw_code if raw_code else "No code content provided"
        
        # 마스킹 수행
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

        # 터미널에서 LLM의 실제 답변을 확인하기 위한 로그 (디버깅용)
        print("\n" + "="*30 + " [LLM RESPONSE] " + "="*30)
        print(raw_text)
        print("="*76 + "\n")

        # 3. 공격적 추출 및 언마스킹 함수
        def robust_extract_and_unmask(field, text):
            # 패턴 1: 표준 JSON 또는 마크다운 형식
            patterns = [
                rf'"{field}"\s*:\s*"(.*?)"(?=\s*,\s*"|\s*}}\s*$|\s*}}?\s*```|$)',
                rf'"{field}"\s*:\s*(.*?)(?=\n\s*"\w+"|$)',
                rf'\*\*{field}\*\*[:\s]+(.*?)(?=\n\*\*|$)',
                rf'{field}[:\s]+(.*?)(?=\n\w+[:\s]|$)'
            ]
            
            for pattern in patterns:
                m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if m:
                    val = m.group(1).strip().strip('"').replace('\\n', '\n').replace('\\"', '"')
                    if len(val) > 2: # 의미 있는 길이일 때만 반환
                        return masker.unmask(val)
            
            # 패턴 2: 키워드 기반 강제 슬라이싱 (패턴 매칭 실패 시)
            try:
                lower_text = text.lower()
                field_lower = field.lower()
                if field_lower in lower_text:
                    idx = lower_text.find(field_lower) + len(field_lower)
                    # 다음 주요 키워드가 나오기 전까지 긁어오기
                    sub = text[idx:].lstrip(' :"\n')
                    # 다른 필드 이름이 나오면 거기서 멈춤
                    stop_words = ["solution", "prevention", "cause", "원인", "해결", "방지"]
                    end_idx = len(sub)
                    for word in stop_words:
                        found = sub.lower().find(word)
                        if 0 < found < end_idx:
                            end_idx = found
                    
                    final_val = sub[:end_idx].strip(' ,}"\n')
                    if len(final_val) > 2:
                        return masker.unmask(final_val)
            except:
                pass

            return f"[{field}] 분석 내용을 추출할 수 없습니다. 로그를 확인하세요."

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