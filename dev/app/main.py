from fastapi import FastAPI
from pydantic import BaseModel
from agent_with_graph import ask_claude

app = FastAPI()

class AnalyzeRequest(BaseModel):
    error_log: str

@app.post("/analyze/log")
async def analyze_log(req: AnalyzeRequest):
    result = ask_claude(req.error_log)
    return {"result": result}
