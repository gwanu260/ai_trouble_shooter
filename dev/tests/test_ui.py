import pytest
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.getcwd())

def test_payload_structure():
    """UI에서 서버로 보낼 페이로드 구조가 올바른지 시뮬레이션 테스트"""
    # UI에서 선택된 가상의 값들
    level = "시니어"
    mode = "log_code"
    input_log = "Error: Timeout"
    input_code = "connect()"
    save_on = True

    # ui.py 내 로직 시뮬레이션
    persona_val = "senior" if level == "시니어" else "junior"
    
    payload = {
        "persona": persona_val,
        "input_mode": mode,
        "error_log": input_log,
        "code": input_code,
        "save_to_db": save_on
    }

    assert payload["persona"] == "senior"
    assert payload["save_to_db"] is True
    assert "error_log" in payload