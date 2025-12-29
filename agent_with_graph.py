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


def ask_claude(user_input: str) -> str:
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    system_prompt = """
너는 서버 에러 로그를 분석하는 AI 개발자 도우미다.
사용자가 입력한 에러 로그를 분석하여 반드시 아래 형식으로만 출력하라.

[원인]
에러의 직접적인 발생 원인을 명확히 설명할 것

[해결책]
즉시 적용 가능한 코드 또는 설정 수정 방법 제시

[재발 방지]
장기적인 관점에서 재발을 막기 위한 가이드 제시

형식은 반드시 유지하고, 불필요한 서론이나 인사말은 출력하지 마라.
"""
    resp = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL_ID"),  # 예: claude-sonnet-4-5-20250929
        max_tokens=1000,
        messages=[{"role": "user", "content": user_input}],
        
    )

    # content 블록 중 text만 합쳐서 반환(안전)
    return "\n".join([b.text for b in resp.content if getattr(b, "type", None) == "text"]).strip()


if __name__ == "__main__":
    print("Agent 시작, 종료시 q 입력")

    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() == "q":
            break

        try:
            answer = ask_claude(user_input)
            print("Agent:", answer)
        except Exception as e:
            print("Agent: 오류 발생:", e)