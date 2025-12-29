from langgraph.graph import StateGraph, END, MessagesState, START
from typing import TypedDict, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
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
load_dotenv()


def ask_claude(system_prompt: str, user_prompt: str) -> str:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    system_prompt = """
너는 서버 에러 로그를 분석하는 AI 개발자 도우미다.

사용자가 입력한 내용을 분석하여
아래 형식으로만 출력하라.
형식, 제목, 줄바꿈을 절대 변경하지 마라.

[원인]
- 에러가 발생한 직접적인 원인을 한 문단으로 설명

[해결책]
- 즉시 적용 가능한 해결 방법을 bullet 형태로 제시

[재발 방지]
- 장기적인 관점의 재발 방지 가이드를 bullet 형태로 제시

규칙:
- Markdown 제목(##, ###) 사용 금지
- 불필요한 설명, 예제 코드, 인사말 금지
- 같은 내용을 반복하지 마라
- 위 3개 섹션 외의 텍스트를 출력하지 마라
"""
    resp = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL_ID"),  # 예: claude-sonnet-4-5-20250929
        max_tokens=1000,
        system=system_prompt,
        messages=[
        {"role": "user", "content": user_input},
    ],
    )
    # content 블록 중 text만 합쳐서 반환(안전)
    return "\n".join([b.text for b in resp.content if getattr(b, "type", None) == "text"]).strip()
