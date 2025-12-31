import pytest
import sys
import os
from fastapi.testclient import TestClient

# 프로젝트 루트를 sys.path에 추가하여 dev.app.main 임포트가 가능하게 함
sys.path.append(os.getcwd())

from dev.app.main import app

@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트를 제공하는 피스쳐"""
    return TestClient(app)

def test_analyze_log_success(client):
    """정상적인 분석 요청 테스트"""
    payload = {
        "persona": "junior",
        "input_mode": "log",
        "error_log": "ZeroDivisionError: division by zero",
        "code": "print(1/0)",
        "save_to_db": False
    }
    response = client.post("/analyze/log", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    # 응답 필드 검증
    assert "cause" in data
    assert "solution" in data
    assert "prevention" in data

def test_analyze_with_save_option(client):
    """저장 옵션을 켰을 때 에러 없이 응답하는지 테스트"""
    payload = {
        "persona": "senior",
        "input_mode": "code",
        "error_log": "",
        "code": "def fast_power(a, b): return a**b",
        "save_to_db": True
    }
    response = client.post("/analyze/log", json=payload)
    assert response.status_code == 200
    # 실제 Pinecone 저장은 BackgroundTasks로 수행되므로 응답 속도와 성공 여부만 확인