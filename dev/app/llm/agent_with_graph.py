from typing import Optional, Literal
from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from dev.app.llm.prompts import PROMPTS
from dev.app.llm.tools import rag_search_tool
# from prompts import PROMPTS
# from tools import rag_search_tool
load_dotenv()

# LLM 설정
llm = ChatAnthropic(
    model=os.getenv("ANTHROPIC_MODEL_ID"),
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.4,
    max_tokens=1000,
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
    log_text = log_text or ""
    code_text = code_text or ""
    if mode == "log":
        return f"[로그]\n{log_text}"
    if mode == "code":
        return f"[코드]\n{code_text}"
    return f"[로그]\n{log_text}\n\n[코드]\n{code_text}"

def agent_draft(state: AgentState):
    persona = state.get("persona", "junior")
    mode = state.get("input_mode", "log")
    system_prompt = PROMPTS[(persona, mode)] + "\n\n[중요] 1차 답변에서는 rag_search를 절대 호출하지 말고, 입력만으로 가능한 분석을 먼저 작성하라."
    msgs = state.get("messages", [])
    if not msgs:
        user_content = build_user_prompt(mode, state.get("log_text") or "", state.get("code_text") or "")
        msgs = [HumanMessage(content=user_content)]
    resp = llm.invoke([SystemMessage(content=system_prompt)] + msgs)
    return {"messages": [resp]}

def need_rag(state: AgentState) -> str:
    # 1차 답변(초안)을 보고 “추가 근거 필요” 판단
    last = state["messages"][-1].content.lower()
    # 이런 표현이 있으면 RAG로 보내기 (원하는 기준으로 튜닝)
    triggers = ["모르겠", "불확실", "추정", "추가 정보", "확인이 필요", "가능성이", "근거 부족"]
    return "tools" if any(t in last for t in triggers) else END

def agent_final(state: AgentState):
    # tools 결과 포함해서 최종 답변 작성 (tool 사용 후니까 tool 추가 호출 중단 안내)
    persona = state.get("persona", "junior")
    mode = state.get("input_mode", "log")
    system_prompt = PROMPTS[(persona, mode)] + "\n\n검색된 지식을 바탕으로 최종 답변을 작성하세요. 추가 도구 호출은 중단하세요."
    msgs = state.get("messages", [])
    resp = llm_with_tools.invoke([SystemMessage(content=system_prompt)] + msgs)
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
    test_state = {
        "messages": [],  # agent_node에서 System/Human 새로 만들어 호출하니 빈 리스트 OK
        "persona": "junior",
        "input_mode": "log",
        "log_text": """
                    Uncaught ReferenceError: count is not defined
                    at increment (main.js:10:14)
                    at HTMLButtonElement.onclick (index.html:25:32)
                    function showUserName(user) {
                    console.log(user.name); // user가 undefined
}
showUserName();
        
        
        
        """,
        "code_text": ""
    }

    out = app.invoke(test_state)
    print("\n=== OUTPUT ===")
    print(out["messages"][-1].content)