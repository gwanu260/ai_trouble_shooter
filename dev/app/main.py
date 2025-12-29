from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class LogRequest(BaseModel):
    log: str

@app.post("/analyze/log")
async def analyze_log(payload: LogRequest):
    log_text = payload.log
    return {
        "error_type": "MockError",
        "message": f"분석된 메시지: {log_text[:50]}...",
        "solution": "해결 예시: 로그를 확인하고 코드를 수정하세요."
    }
