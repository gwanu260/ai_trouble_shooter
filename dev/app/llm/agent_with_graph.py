from typing import Optional, Literal
from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from dev.app.llm.prompts import PROMPTS
from dev.app.llm.tools import rag_search_tool

load_dotenv()

# LLM 설정
llm = ChatAnthropic(
    model=os.getenv("ANTHROPIC_MODEL_ID"),
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.4,
    max_tokens=1500,
)

class AgentState(MessagesState):
    persona: str
    input_mode: str
    log_text: str | None
    code_text: str | None

# Tool 설정
tools = [rag_search_tool]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

def build_user_prompt(mode: str, log_text: str, code_text: str) -> str:
    # 텍스트가 있을 경우 양끝 공백을 먼저 제거합니다.
    log_text = (log_text or "").strip()
    code_text = (code_text or "").strip()
    
    if mode == "log":
        content = f"[로그]\n{log_text}"
    elif mode == "code":
        content = f"[코드]\n{code_text}"
    else:
        content = f"[로그]\n{log_text}\n\n[코드]\n{code_text}"
    
    return content.strip()

def agent_draft(state: AgentState):
    persona = state.get("persona", "junior")
    mode = state.get("input_mode", "log")
    
    # 시스템 프롬프트 조립 시 줄바꿈 뒤에 공백이 생기지 않도록 strip()
    base_prompt = PROMPTS.get((persona, mode), "분석가 페르소나로 동작하세요.")
    system_prompt = (base_prompt + "\n\n[중요] 1차 답변에서는 rag_search를 절대 호출하지 말고, 입력만으로 가능한 분석을 먼저 작성하라.").strip()
    
    msgs = state.get("messages", [])
    if not msgs:
        user_content = build_user_prompt(mode, state.get("log_text") or "", state.get("code_text") or "")
        msgs = [HumanMessage(content=user_content)]
    
    # [핵심] Anthropic 400 에러 방지: 모든 메시지의 끝 공백 강제 제거
    formatted_msgs = [SystemMessage(content=system_prompt)] + msgs
    for m in formatted_msgs:
        if hasattr(m, "content") and isinstance(m.content, str):
            m.content = m.content.strip()

    resp = llm.invoke(formatted_msgs)
    return {"messages": [resp]}

def need_rag(state: AgentState) -> str:
    # 1차 답변을 보고 RAG 호출 여부 판단
    last_content = state["messages"][-1].content
    if not last_content:
        return END
    
    last = last_content.lower()
    triggers = ["모르겠", "불확실", "추정", "추가 정보", "확인이 필요", "가능성이", "근거 부족"]
    return "tools" if any(t in last for t in triggers) else END

def agent_final(state: AgentState):
    persona = state.get("persona", "junior")
    mode = state.get("input_mode", "log")
    
    base_prompt = PROMPTS.get((persona, mode), "분석가 페르소나로 동작하세요.")
    system_prompt = (base_prompt + "\n\n검색된 지식을 바탕으로 최종 답변을 작성하세요. 추가 도구 호출은 중단하세요.").strip()
    
    msgs = state.get("messages", [])
    
    # 모든 메시지의 content에서 trailing whitespace 제거
    formatted_msgs = [SystemMessage(content=system_prompt)] + msgs
    for m in formatted_msgs:
        if hasattr(m, "content") and isinstance(m.content, str):
            m.content = m.content.strip()

    resp = llm_with_tools.invoke(formatted_msgs)
    return {"messages": [resp]}

# 그래프 정의
graph = StateGraph(AgentState)
graph.add_node("draft", agent_draft)
graph.add_node("tools", tool_node)
graph.add_node("final", agent_final)

graph.add_edge(START, "draft")
graph.add_conditional_edges("draft", need_rag, {"tools": "tools", END: END})
graph.add_edge("tools", "final")
graph.add_edge("final", END)

app = graph.compile()

if __name__ == "__main__":
    # 테스트 시에도 불필요한 공백이 포함되지 않도록 strip() 적용
    test_log = """
Uncaught ReferenceError: count is not defined
at increment (main.js:10:14)
at HTMLButtonElement.onclick (index.html:25:32)
function showUserName(user) {
    console.log(user.name); 
}
showUserName();
""".strip()

    test_state = {
        "messages": [],
        "persona": "junior",
        "input_mode": "log",
        "log_text": test_log,
        "code_text": ""
    }

    out = app.invoke(test_state)
    print("\n=== OUTPUT ===")
    if out["messages"]:
        print(out["messages"][-1].content)