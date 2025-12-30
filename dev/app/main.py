from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import json
import re
from agent_with_graph import app as app_graph

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

# 1. DB 저장 함수 (더미 데이터 생성 및 저장)
def save_to_dummy_db(req: AnalyzeRequest):
    """분석 요청 데이터를 DB에 기록하는 로직"""
    print(f"\n[DB SAVE] 분석 데이터를 저장합니다...")
    log_preview = (req.error_log[:50] + "...") if req.error_log else "N/A"
    print(f" > Persona: {req.persona} | Mode: {req.input_mode}")
    print(f" > Log Preview: {log_preview}")
    # 실제 구현 시 여기서 DB 연동 코드를 작성합니다.
    return True

@app.post("/analyze/log", response_model=AnalyzeResponse)
async def analyze_log(req: AnalyzeRequest):
    try:
        # Step 1: 데이터 저장
        save_to_dummy_db(req)
        
        print(f"\n[REQUEST] Persona: {req.persona}, Mode: {req.input_mode}")
        
        # Step 2: 그래프 실행 (messages를 비워주면 agent_node에서 생성함)
        initial_state = {
            "messages": [], 
            "persona": req.persona,
            "input_mode": req.input_mode,
            "log_text": req.error_log,
            "code_text": req.code
        }

        final_state = app_graph.invoke(initial_state)
        raw_text = final_state["messages"][-1].content
        print(f"\n[AI RAW OUTPUT]\n{raw_text}\n" + "="*50)

        # Step 3: 필드 추출 함수 (robust_extract)
        def robust_extract(field, text):
            pattern = rf'"{field}"\s*:\s*"(.*?)"(?=\s*,\s*"|\s*}}\s*$|\s*}}?\s*```|$)'
            m = re.search(pattern, text, re.DOTALL)
            if m:
                return m.group(1).replace('\\n', '\n').replace('\\"', '"').strip()
            
            if field == "prevention":
                last_pattern = r'"prevention"\s*:\s*"(.*)'
                m = re.search(last_pattern, text, re.DOTALL)
                if m:
                    content = m.group(1)
                    content = re.sub(r'"\s*\}?\s*```?.*$', '', content, flags=re.DOTALL).strip()
                    return content.replace('\\n', '\n').replace('\\"', '"')
            return None

        cause_val = robust_extract("cause", raw_text)
        sol_val = robust_extract("solution", raw_text)
        prev_val = robust_extract("prevention", raw_text)

        # 결과 조합
        if cause_val or sol_val or prev_val:
            return {
                "cause": cause_val or "원인을 분석 중입니다...",
                "solution": sol_val or "해결책을 생성 중입니다...",
                "prevention": prev_val or "코드 품질 향상을 위해 노력하세요."
            }

        # 전체 JSON 파싱 시도 (Fallback)
        try:
            cleaned_text = re.sub(r'```json\s*|```\s*', '', raw_text).strip()
            match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            json_str = match.group() if match else cleaned_text
            json_data = json.loads(json_str, strict=False)
            return {
                "cause": json_data.get("cause", "분석 실패"),
                "solution": json_data.get("solution", "해결책 생성 실패"),
                "prevention": json_data.get("prevention", "가이드 없음")
            }
        except Exception:
            return {"cause": "응답 처리 오류", "solution": "재시도 요망", "prevention": raw_text[:200]}

    except Exception as e:
        print(f"Server Critical Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))