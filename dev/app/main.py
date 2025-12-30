from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import json
import re
from langchain_core.messages import HumanMessage
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

@app.post("/analyze/log", response_model=AnalyzeResponse)
async def analyze_log(req: AnalyzeRequest):
    try:
        print(f"\n[REQUEST] Persona: {req.persona}, Mode: {req.input_mode}")
        
        initial_state = {
            "messages": [HumanMessage(content="analyze")],
            "persona": req.persona,
            "input_mode": req.input_mode,
            "log_text": req.error_log,
            "code_text": req.code
        }

        final_state = app_graph.invoke(initial_state)
        raw_text = final_state["messages"][-1].content
        print(f"\n[AI RAW OUTPUT]\n{raw_text}\n" + "="*50)

        # 🛠️ 더욱 유연해진 필드 추출 함수
        def robust_extract(field, text):
            # 1. 일반적인 패턴 시도: "field": "value" (다음 필드 혹은 닫는 중괄호 전까지)
            pattern = rf'"{field}"\s*:\s*"(.*?)"(?=\s*,\s*"|\s*}}\s*$|\s*}}?\s*```|$)'
            m = re.search(pattern, text, re.DOTALL)
            if m:
                return m.group(1).replace('\\n', '\n').replace('\\"', '"').strip()
            
            # 2. 마지막 필드(prevention) 전용: 닫는 따옴표가 불안정할 경우를 대비
            if field == "prevention":
                # "prevention" 문자열 이후부터 마지막까지 다 긁어옴
                last_pattern = r'"prevention"\s*:\s*"(.*)'
                m = re.search(last_pattern, text, re.DOTALL)
                if m:
                    content = m.group(1)
                    # 뒤에 남은 불필요한 JSON 기호들( ", }, ``` )을 강제로 제거
                    content = re.sub(r'"\s*\}?\s*```?.*$', '', content, flags=re.DOTALL).strip()
                    return content.replace('\\n', '\n').replace('\\"', '"')
            return None

        # 1. 각 필드별 개별 추출
        cause_val = robust_extract("cause", raw_text)
        sol_val = robust_extract("solution", raw_text)
        prev_val = robust_extract("prevention", raw_text)

        # 2. 결과 조합 (하나라도 성공했다면 최대한 보여줌)
        # 모든 필드가 None인 경우에만 Fallback(3번)으로 이동
        if cause_val or sol_val or prev_val:
            return {
                "cause": cause_val or "원인을 분석 중입니다...",
                "solution": sol_val or "해결책을 생성 중입니다...",
                "prevention": prev_val or "향후 코드 품질을 위해 지속적인 리팩토링을 권장합니다."
            }

        # 3. 최후의 수단: 전체 JSON 파싱 시도
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
            # 4. 정말 모든 것이 실패했을 때
            return {
                "cause": "응답을 처리하는 중 오류가 발생했습니다.",
                "solution": "AI 응답 형식이 불안정합니다. 잠시 후 다시 시도해주세요.",
                "prevention": raw_text[:200]  # 원문의 앞부분이라도 노출
            }

    except Exception as e:
        print(f"Server Critical Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))