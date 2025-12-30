import os
from typing import TypedDict, List, Optional, Literal
from dotenv import load_dotenv
from anthropic import Anthropic
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from prompts import PROMPTS 

load_dotenv()

# 1. 상태 정의
class AgentState(TypedDict):
    messages: List[BaseMessage]
    persona: Literal["junior", "senior"]
    input_mode: Literal["log", "code", "log_code"]
    log_text: Optional[str]
    code_text: Optional[str]

# 2. 클로드 호출 공통 로직
def call_anthropic(system_prompt: str, user_content: str) -> str:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL_ID"),
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return "".join([b.text for b in resp.content if hasattr(b, 'text')]).strip()

# 3. 노드 생성 팩토리
def make_node(persona: str, mode: str):
    def node(state: AgentState):
        system_prompt = PROMPTS.get((persona, mode), "에러 분석 전문가입니다.")
        
        # 입력 데이터 구성
        user_content = ""
        if state["log_text"]: user_content += f"[에러 로그]\n{state['log_text']}\n\n"
        if state["code_text"]: user_content += f"[코드 스니펫]\n{state['code_text']}"
        
        result = call_anthropic(system_prompt, user_content)
        return {"messages": [AIMessage(content=result)]}
    return node

# 4. 라우터 함수
def router(state: AgentState):
    return f"{state['persona']}_{state['input_mode']}"

# 5. 그래프 구축
builder = StateGraph(AgentState)

# 노드 등록 (6가지 조합)
modes = ["log", "code", "log_code"]
personas = ["junior", "senior"]

for p in personas:
    for m in modes:
        node_id = f"{p}_{m}"
        builder.add_node(node_id, make_node(p, m))
        builder.add_edge(node_id, END)

builder.add_conditional_edges(
    START, 
    router, 
    {f"{p}_{m}": f"{p}_{m}" for p in personas for m in modes}
)

# 최종 컴파일된 그래프 객체
app = builder.compile()