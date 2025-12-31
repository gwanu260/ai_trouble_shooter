# dev/tests/llm/test_llm_smoke.py
import json
import importlib
import re

import pytest


def _count_sentences_ko(text: str) -> int:
    """
    prevention 최소 2문장 규칙 검증용(대충이라도 문장 경계를 센다)
    - 한국어/영문 혼합을 고려해서 마침표/물음표/느낌표/줄바꿈 기반으로 분리
    """
    parts = [p.strip() for p in re.split(r"[.!?]\s+|\n+", text) if p.strip()]
    return len(parts)


class FakeLLM:
    """
    CI에서 외부 API 호출을 막기 위한 Fake LLM.
    - bind_tools: 그대로 self 반환
    - invoke: tool call 없이, JSON ONLY 형태의 content를 가진 메시지를 반환
    """
    def __init__(self, *args, **kwargs):
        pass

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        # langchain_core.messages.AIMessage를 사용하면 tools_condition이 잘 처리함
        from langchain_core.messages import AIMessage

        payload = {
            "cause": "테스트용 원인입니다. (Fake LLM)",
            "solution": "테스트용 해결 방법입니다. (Fake LLM)",
            "prevention": "재발 방지를 위해 입력 검증을 추가하세요.\\n환경 변수를 실행 전에 점검하는 preflight 체크를 권장합니다."
        }
        # JSON ONLY 규칙에 맞게 문자열 반환
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))


@pytest.fixture
def ag_module(monkeypatch):
    """
    agent_with_graph 모듈을 'FakeLLM' 기반으로 import/reload 해서 반환.
    - 핵심: ChatAnthropic을 FakeLLM으로 바꿔치기한 뒤 모듈을 import해야
      모듈 전역에서 llm/llm_with_tools/app 생성이 안전하게 된다.
    """

    # 1) ChatAnthropic을 FakeLLM으로 패치
    import langchain_anthropic
    monkeypatch.setattr(langchain_anthropic, "ChatAnthropic", FakeLLM)

    # 2) 혹시 env가 None이라 코드가 흔들릴 수 있으니 더미로 채워둠(안전장치)
    monkeypatch.setenv("ANTHROPIC_MODEL_ID", "fake-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

    # 3) 너희 모듈 import (여기만 경로 맞춰 수정!)
    # 예시들:
    #   import agent_with_graph as ag
    #   import dev.llm.agent_with_graph as ag
    #   from dev.llm import agent_with_graph as ag
    from dev.llm import agent_with_graph as ag  # <-- 너희 파일 위치에 맞게 수정

    # 4) 이미 import 되어 있을 수 있으니 reload로 확실히 반영
    ag = importlib.reload(ag)
    return ag


def test_graph_builds_and_app_exists(ag_module):
    """
    (1) 그래프/앱이 깨지지 않고 생성되는지(=빌드 smoke test)
    """
    ag = ag_module

    # app이 compile되어 invoke 가능해야 함
    assert hasattr(ag, "app")
    assert callable(getattr(ag.app, "invoke", None))

    # 핵심 노드/그래프 구성 요소가 존재하는지도 가볍게 체크
    assert hasattr(ag, "graph")
    assert hasattr(ag, "agent_node")


def test_app_invoke_returns_json_contract(ag_module):
    """
    (2) app.invoke 결과가 JSON 계약을 지키는지 확인
    - cause/solution/prevention 키 존재
    - JSON 파싱 가능
    - prevention이 최소 2문장(또는 줄바꿈 기반 2개 이상)인지
    """
    ag = ag_module

    test_state = {
        "messages": [],
        "persona": "junior",
        "input_mode": "log",
        "log_text": "ValidationException: The provided model identifier is invalid.",
        "code_text": ""
    }

    out = ag.app.invoke(test_state)
    assert "messages" in out
    assert len(out["messages"]) >= 1

    last = out["messages"][-1]
    content = getattr(last, "content", "")
    assert isinstance(content, str) and content.strip(), "LLM output content should be a non-empty string"

    # JSON parse
    data = json.loads(content)

    # contract keys
    for k in ("cause", "solution", "prevention"):
        assert k in data, f"Missing key: {k}"
        assert isinstance(data[k], str) and data[k].strip(), f"Field '{k}' should be a non-empty string"

    # prevention: 최소 2문장 이상(너희 룰)
    assert _count_sentences_ko(data["prevention"]) >= 2, "prevention must be at least 2 sentences"
