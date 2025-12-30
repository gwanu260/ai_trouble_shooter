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


def ask_claude2(user_input: str) -> str:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    system_prompt = """
너는 파이썬 에러 분석 전문가다. 반드시 아래 JSON 형식으로만 답변하라. 
다른 텍스트는 절대 포함하지 마라.

{
  "cause": "에러 원인 설명",
  "solution": "해결 방법 (리스트 형태도 문자열로 작성)",
  "prevention": "재발 방지 가이드"
}

규칙:
- Markdown 제목(##, ###) 사용 금지
- 불필요한 설명, 예제 코드, 인사말 금지
- 같은 내용을 반복하지 마라
- 위 3개 섹션 외의 텍스트를 출력하지 마라
"""
    
    resp = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL_ID"),
        max_tokens=1000,
        system=system_prompt,  # 여기에 시스템 프롬프트를 명시해야 합니다!
        messages=[
            {"role": "user", "content": user_input},
        ],
    )
    return "\n".join([b.text for b in resp.content if getattr(b, "type", None) == "text"]).strip()