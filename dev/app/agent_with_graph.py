from typing import Optional, Literal
from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_anthropic import ChatAnthropic
from dev.app.prompts import PROMPTS
from dev.app.tools import rag_search_tool

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

def agent_node(state: AgentState):
    persona = state.get("persona", "junior")
    mode = state.get("input_mode", "log")
    
    # 1. 페르소나에 맞는 시스템 프롬프트 로드
    system_prompt = PROMPTS[(persona, mode)]
    
    # 2. 메시지 기록 관리
    current_messages = state.get("messages", [])
    
    # 처음 실행 시 유저 입력 구성
    if not current_messages:
        user_content = build_user_prompt(
            mode, 
            state.get("log_text") or "", 
            state.get("code_text") or ""
        )
        current_messages = [HumanMessage(content=user_content)]

    # 3. 도구 사용 여부 확인 (도구를 이미 사용했다면 요약 답변 유도)
    used_tool = any(isinstance(m, ToolMessage) for m in current_messages)
    
    final_system_msg = system_prompt
    if used_tool:
        final_system_msg += "\n\n검색된 지식을 바탕으로 최종 답변을 작성하세요. 추가 도구 호출은 중단하세요."

    # 4. LLM 호출
    full_input = [SystemMessage(content=final_system_msg)] + current_messages
    response = llm_with_tools.invoke(full_input)

    # MessagesState는 리스트를 반환하면 자동으로 합쳐짐
    return {"messages": [response]}

# 그래프 정의
graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "agent")

graph.add_conditional_edges(
    "agent",
    tools_condition,
    {
        "tools": "tools",
        END: END,
    },
)

graph.add_edge("tools", "agent")

app = graph.compile()