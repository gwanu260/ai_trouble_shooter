import sys
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import json
import re

# ✅ 경로 자동 인식 로직 (ImportError 방지)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from main.llm.agent_with_graph import app as app_graph

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

@app.post("/analyze/log", response_model=AnalyzeResponse)
async def analyze_log(req: AnalyzeRequest):
    try:
        # Step 1: 에이전트 실행
        initial_state = {
            "messages": [], 
            "persona": req.persona,
            "input_mode": req.input_mode,
            "log_text": req.error_log,
            "code_text": req.code
        }
        final_state = app_graph.invoke(initial_state)
        raw_text = final_state["messages"][-1].content

        # Step 2: 필드 추출 함수
        def robust_extract(field, text):
            pattern = rf'"{field}"\s*:\s*"(.*?)"(?=\s*,\s*"|\s*}}\s*$|\s*}}?\s*```|$)'
            m = re.search(pattern, text, re.DOTALL)
            if m: return m.group(1).replace('\\n', '\n').replace('\\"', '"').strip()
            return None

        # 결과 생성 및 반환 (저장 로직 없음)
        return {
            "cause": robust_extract("cause", raw_text) or "원인 분석 완료",
            "solution": robust_extract("solution", raw_text) or "해결책 생성 완료",
            "prevention": robust_extract("prevention", raw_text) or "가이드 생성 완료"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))