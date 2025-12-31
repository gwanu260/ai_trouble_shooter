from fastapi import FastAPI

app = FastAPI()

@app.post("/analyze/log")
async def analyze_log(payload: dict):
    """
    테스트를 위한 Mock 응답
    """
    return {
        "status": "ok",
        "message": "analysis complete",
        "received": payload
    }