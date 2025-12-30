from langgraph.graph import StateGraph, END, MessagesState, START
from typing import TypedDict, List, Optional, Literal
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_aws import ChatBedrockConverse, ChatBedrock
from langgraph.prebuilt import ToolNode, tools_condition
from dotenv import load_dotenv
import os
import boto3
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from anthropic import Anthropic
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import ToolNode, tools_condition
from prompts import PROMPTS
from tools import rag_search_tool

load_dotenv()

llm = ChatAnthropic(
    model=os.getenv("ANTHROPIC_MODEL_ID"),  # ex) claude-3-sonnet-20240229
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.4,
    max_tokens=1000,
)
class AgentState(MessagesState):
    persona: str          # "junior" | "senior"
    input_mode: str       # "log" | "code" | "log_code"
    log_text: str | None
    code_text: str | None

tools = [rag_search_tool]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)

# ------------------------------
# def agent_node(state: AgentState):
#     response = llm_with_tools.invoke(state["messages"])
#     return {"messages": [response]}
# ------------------------------

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

    system_prompt = PROMPTS[(persona, mode)]
    user_prompt = build_user_prompt(
        mode,
        state.get("log_text") or "",
        state.get("code_text") or "",
    )

    # 🔑 이미 tool을 썼는지 판단 (state 기준)
    used_tool = any(isinstance(m, ToolMessage) for m in state.get("messages", []))

    if not used_tool:
        user_prompt += "\n\n필요하면 rag_search 도구를 사용해 관련 지식을 조회한 뒤 답해라."
    else:
        user_prompt += "\n\n이미 제공된 정보를 바탕으로 최종 답변만 작성하라. 추가 도구 호출은 하지 마라."

    new_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    # ✅ 핵심 수정: state["messages"] + new_messages
    response = llm_with_tools.invoke(
        state.get("messages", []) + new_messages
    )

    return {
        "messages": state.get("messages", []) + [response]
    }


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

if __name__ == "__main__":
    test_state = {
        "messages": [],  # agent_node에서 System/Human 새로 만들어 호출하니 빈 리스트 OK
        "persona": "junior",
        "input_mode": "log",
        "log_text": "ValidationException: The provided model identifier is invalid.",
        "code_text": ""
    }

    out = app.invoke(test_state)
    print("\n=== OUTPUT ===")
    print(out["messages"][-1].content)