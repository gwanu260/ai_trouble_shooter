from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import json  # JSON 파싱을 위해 추가
from agent_with_graph2 import ask_claude2

app = FastAPI()

class AnalyzeRequest(BaseModel):
    error_log: str
    code_snippet: Optional[str] = None

class AnalyzeResponse(BaseModel):
    cause: str
    solution: str
    prevention: str

@app.post("/analyze/log", response_model=AnalyzeResponse)
async def analyze_log(req: AnalyzeRequest):
    try:
        # 1. 입력 데이터 결합
        user_content = f"Error Log:\n{req.error_log}"
        if req.code_snippet:
            user_content += f"\n\nCode Snippet:\n{req.code_snippet}"

        # 2. LLM 호출 (이제 JSON 문자열이 반환됨)
        raw_text = ask_claude2(user_content)

        # 3. JSON 파싱
        # LLM이 간혹 JSON 앞뒤에 설명을 붙일 경우를 대비해 처리 로직을 넣으면 더 안전합니다.
        try:
            # 문자열에서 JSON 부분만 추출 (가장 간단한 형태)
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}') + 1
            json_data = json.loads(raw_text[start_idx:end_idx])
            
            return {
                "cause": json_data.get("cause", "원인 분석 실패"),
                "solution": json_data.get("solution", "해결책 생성 실패"),
                "prevention": json_data.get("prevention", "방지 가이드 실패")
            }
        except (json.JSONDecodeError, ValueError):
            # JSON 파싱 실패 시 기본값 반환
            print(f"JSON Parsing Error. Raw Text: {raw_text}")
            raise HTTPException(status_code=500, detail="AI가 올바른 형식으로 응답하지 않았습니다.")

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))