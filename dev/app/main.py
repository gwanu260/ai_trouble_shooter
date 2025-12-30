from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal
import json
import re  # 정규표현식 추가
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
        # 1. 초기 상태 설정 및 로그 출력
        print(f"\n[REQUEST] Persona: {req.persona}, Mode: {req.input_mode}")
        
        initial_state = {
            "messages": [HumanMessage(content="analyze")],
            "persona": req.persona,
            "input_mode": req.input_mode,
            "log_text": req.error_log,
            "code_text": req.code
        }

        # 2. 랭그래프 실행
        final_state = app_graph.invoke(initial_state)
        raw_text = final_state["messages"][-1].content
        
        # [디버깅용] AI가 실제로 뱉은 날것의 텍스트 확인
        print(f"\n[AI RAW OUTPUT]\n{raw_text}\n" + "="*50)

        # 3. 강화된 JSON 추출 로직
        try:
            # [수정된 핵심 로직]
            # 1. ```json 이나 ``` 같은 마크다운 태그를 제거
            cleaned_text = re.sub(r'```json\s*|```\s*', '', raw_text).strip()
            
            # 2. 정규표현식으로 가장 바깥쪽의 { } 덩어리만 추출
            match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            
            if not match:
                raise ValueError("JSON 구조를 찾을 수 없습니다.")
            
            json_str = match.group()
            
            # 3. 파이썬 JSON 파서가 읽을 수 있도록 특수 기호 처리 (strict=False)
            json_data = json.loads(json_str, strict=False)
            
            return {
                "cause": json_data.get("cause", "원인 분석 실패"),
                "solution": json_data.get("solution", "해결책 생성 실패"),
                "prevention": json_data.get("prevention", "가이드 없음")
            }
            
        except Exception as e:
            # 여전히 실패할 경우를 대비한 최후의 수단 (키워드 추출)
            print(f"Parsing error details: {e}")
            
            # 정규식으로 각 필드 내용만 억지로 뜯어냄
            cause = re.search(r'"cause":\s*"(.*?)"', raw_text, re.DOTALL)
            solution = re.search(r'"solution":\s*"(.*?)"', raw_text, re.DOTALL)
            prevention = re.search(r'"prevention":\s*"(.*?)"', raw_text, re.DOTALL)
            
            return {
                "cause": cause.group(1).replace("\\n", "\n") if cause else "파싱 실패: 원문을 확인하세요.",
                "solution": solution.group(1).replace("\\n", "\n") if solution else raw_text,
                "prevention": prevention.group(1).replace("\\n", "\n") if prevention else "프롬프트 확인 필요"
            }

    except Exception as e:
        print(f"Server Critical Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))