import sys
import os

# ✅ 파일 위치 기준 루트 경로 계산 및 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pytest
from fastapi.testclient import TestClient
from dev.app.main import app 

@pytest.fixture
def client():
    return TestClient(app)

def test_analyze_api_flow(client):
    """분석 API가 정상적으로 응답하는지 테스트"""
    payload = {
        "persona": "junior",
        "input_mode": "log",
        "error_log": "NameError: name 'x' is not defined",
        "code": "print(x)"
    }
    response = client.post("/analyze/log", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert all(k in data for k in ["cause", "solution", "prevention"])