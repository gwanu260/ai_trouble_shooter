import json
import importlib
import re
import pytest

def _count_sentences_ko(text: str) -> int:
    text = text.replace("\\n", "\n")
    parts = [p.strip() for p in re.split(r"[.!?]\s+|\n+", text) if p.strip()]
    return len(parts)

class FakeLLM:
    def __init__(self, *args, **kwargs):
        pass
    def bind_tools(self, tools):
        return self
    def invoke(self, messages):
        from langchain_core.messages import AIMessage
        payload = {
            "cause": "테스트용 원인입니다. (Fake LLM)",
            "solution": "테스트용 해결 방법입니다. (Fake LLM)",
            "prevention": "재발 방지를 위해 입력 검증을 추가하세요.\n환경 변수를 점검하세요."
        }
        return AIMessage(content=json.dumps(payload, ensure_ascii=False))

@pytest.fixture
def ag_module(monkeypatch):
    import langchain_anthropic
    monkeypatch.setattr(langchain_anthropic, "ChatAnthropic", FakeLLM)
    monkeypatch.setenv("ANTHROPIC_MODEL_ID", "fake-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    
    # 경로에 맞춰 import (현재 구조 반영)
    from dev.app.llm import agent_with_graph as ag
    ag = importlib.reload(ag)
    return ag

def test_graph_builds_and_app_exists(ag_module):
    ag = ag_module
    assert hasattr(ag, "app")
    assert callable(getattr(ag.app, "invoke", None))

    # [수정] 실제 존재하는 노드 이름으로 검증
    assert hasattr(ag, "graph")
    assert hasattr(ag, "agent_draft") # 기존 agent_node에서 수정
    assert hasattr(ag, "agent_final") # 추가된 노드 검증

def test_app_invoke_returns_json_contract(ag_module):
    ag = ag_module
    test_state = {
        "messages": [],
        "persona": "junior",
        "input_mode": "log",
        "log_text": "ValidationException",
        "code_text": ""
    }
    out = ag.app.invoke(test_state)
    assert "messages" in out
    last = out["messages"][-1]
    content = getattr(last, "content", "")
    data = json.loads(content)
    for k in ("cause", "solution", "prevention"):
        assert k in data
    assert _count_sentences_ko(data["prevention"]) >= 2