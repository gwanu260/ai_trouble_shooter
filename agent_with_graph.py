from langgraph.graph import StateGraph, END, MessagesState, START
from typing import TypedDict, List, Optional, Literal
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
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
from prompts import PROMPTS
from tools import rag_search

load_dotenv()


def ask_claude(system_prompt: str, user_prompt: str) -> str:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    resp = client.messages.create(
    model=os.getenv("ANTHROPIC_MODEL_ID"),
    max_tokens=1000,
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
)
    # content 블록 중 text만 합쳐서 반환(안전)
    return "\n".join([b.text for b in resp.content if getattr(b, "type", None) == "text"]).strip()

class AgentState(MessagesState):
    persona: Literal["junior", "senior"]
    input_mode: Literal["log", "code", "log_code"]
    log_text: Optional[str]
    code_text: Optional[str]

def router(state: AgentState) -> str:
    persona = state.get("persona", "junior")
    mode = state.get("input_mode", "log")

    if persona == "junior" and mode == "log":
        return "junior_log"
    if persona == "junior" and mode == "code":
        return "junior_code"
    if persona == "junior" and mode == "log_code":
        return "junior_log_code"

    if persona == "senior" and mode == "log":
        return "senior_log"
    if persona == "senior" and mode == "code":
        return "senior_code"
    return "senior_log_code"   

def make_analyze_node(persona: Literal["junior", "senior"], mode: Literal["log", "code", "log_code"]):
    def node(state: AgentState):
        system_prompt = PROMPTS[(persona, mode)]

        log_text = state.get("log_text") or ""
        code_text = state.get("code_text") or ""

        if mode == "log":
            user_prompt = f"[로그]\n{log_text}"
        elif mode == "code":
            user_prompt = f"[코드]\n{code_text}"
        else:
            user_prompt = f"[로그]\n{log_text}\n\n[코드]\n{code_text}"

        result = ask_claude(system_prompt, user_prompt)

        return {"messages": [AIMessage(content=result)]}

    return node

# -------------------------
# 2-5) 그래프 구성
# -------------------------
graph = StateGraph(AgentState)

graph.add_node("junior_log", make_analyze_node("junior", "log"))
graph.add_node("junior_code", make_analyze_node("junior", "code"))
graph.add_node("junior_log_code", make_analyze_node("junior", "log_code"))
graph.add_node("senior_log", make_analyze_node("senior", "log"))
graph.add_node("senior_code", make_analyze_node("senior", "code"))
graph.add_node("senior_log_code", make_analyze_node("senior", "log_code"))

graph.add_conditional_edges(
    START,
    router,
    {
        "junior_log": "junior_log",
        "junior_code": "junior_code",
        "junior_log_code": "junior_log_code",
        "senior_log": "senior_log",
        "senior_code": "senior_code",
        "senior_log_code": "senior_log_code",
    },
)

for n in [
    "junior_log",
    "junior_code",
    "junior_log_code",
    "senior_log",
    "senior_code",
    "senior_log_code",
]:
    graph.add_edge(n, END)

app = graph.compile()


# -------------------------
# 2-6) CLI 테스트 (원하면 제거)
# -------------------------
if __name__ == "__main__":
    print("Agent 시작, 종료시 q 입력")
    print("예) persona=junior|senior, mode=log|code|log_code")

    while True:
        persona = input("\npersona(junior/senior): ").strip().lower()
        if persona == "q":
            break
        mode = input("mode(log/code/log_code): ").strip().lower()
        if mode == "q":
            break

        if mode == "log":
            log_text = input("\n[로그 입력]\n> ")
            code_text = ""
        elif mode == "code":
            log_text = ""
            code_text = input("\n[코드 입력]\n> ")
        else:
            log_text = input("\n[로그 입력]\n> ")
            code_text = input("\n[코드 입력]\n> ")

        state: AgentState = {
            "messages": [HumanMessage(content="analyze")],
            "persona": "senior" if persona == "senior" else "junior",
            "input_mode": "log_code" if mode == "log_code" else ("code" if mode == "code" else "log"),
            "log_text": log_text,
            "code_text": code_text,
        }

        try:
            out = app.invoke(state)
            print("\nAgent:\n", out["messages"][-1].content)
        except Exception as e:
            print("Agent: 오류 발생:", e)