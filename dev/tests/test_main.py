import sys
import os
import pytest
from fastapi.testclient import TestClient

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, root_dir)

from dev.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_analyze_and_then_save_flow(client):
    # 1. 분석 테스트
    analyze_payload = {
        "persona": "junior", "input_mode": "log",
        "error_log": "Test Error", "code": "test()"
    }
    analyze_res = client.post("/analyze/log", json=analyze_payload)
    assert analyze_res.status_code == 200
    result = analyze_res.json()

    # 2. 저장 테스트
    save_payload = {
        "persona": "junior",
        "error_log": "Test Error",
        "code": "test()",
        "cause": result["cause"],
        "solution": result["solution"]
    }
    save_res = client.post("/save/result", json=save_payload)
    assert save_res.status_code == 200
    assert save_res.json()["status"] == "success"