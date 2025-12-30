'''
A2A (Agent-to-Agent) 아키텍처

- 하나의 거대 모델이 모든 것을 처리하는 것이 아니라, 
- 전문화된 페르소나를 가진 에이전트들이 서로의 결과물을 입력받아 작업을 고도화하는 방식
    1) User Task: 사용자가 주제를 던짐
    2) Agent A (Developer): 요청을 받아 1차 코드를 작성
    3) Agent B (Reviewer): 작성된 코드를 분석하여 버그나 보안 취약점을 지적
    4) Feedback Loop: Developer 에이전트는 Reviewer의 지적을 바탕으로 코드를 수정
- 설치
    - pip install boto3 langchain-aws langchain-core
- "순차적 협업(Sequential Collaboration)" 패턴
    1. 에이전트 정의 (Role Definition)
        - Developer Agent: "구현"에 집중하는 프롬프트를 가집니다. 창의적이고 생산적인 역할
        - Reviewer Agent: "비판"과 "분석"에 집중하는 프롬프트를 가집니다. 논리적이고 검증적인 역할
        - Point: Bedrock의 Claude 모델은 성능이 뛰어나므로, 프롬프트(System Prompt)만 바꾸면 완전히 다른 전문가처럼 행동함
    2. 메시지 전달 (Message Passing)
        - A2A의 핵심은 한 에이전트의 출력이 다른 에이전트의 입력이 되는 것임
        - draft_code (Developer의 출력) ➡️ reviewer_agent의 입력
        - feedback (Reviewer의 출력) ➡️ refiner_agent의 입력
    3. 피드백 루프 (Feedback Loop)
        - 단순히 일을 시키고 끝나는 것이 아니라, 리뷰 결과에 따라 행동을 결정함
- 위 코드에서는 if "PASS" not in feedback: 
    - 조건을 통해 개선이 필요한 경우에만 에이전트가 다시 작동하도록 제어 흐름(Control Flow)을 만들었슴

'''

import boto3
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import dotenv
dotenv.load_dotenv()

# 1. 공통 Bedrock LLM 설정
# (두 에이전트가 같은 "두뇌"를 쓰지만 다른 "역할(Prompt)"을 가집니다)
llm = ChatBedrock(
    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
    #region="ap-northeast-1",
    client=boto3.client("bedrock-runtime", region_name="ap-northeast-1"),
    model_kwargs={"temperature": 0.7}
)

# --- Agent 1: 주니어 개발자 (Developer) ---
# 역할: 요청받은 기능을 Python 코드로 구현
developer_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 열정적인 '신입 파이썬 개발자'입니다. 요청받은 기능을 구현하는 코드를 작성하세요. 설명은 최소화하고 코드 위주로 작성하세요."),
    ("user", "{request}")
])
developer_agent = developer_prompt | llm | StrOutputParser()

# --- Agent 2: 시니어 리뷰어 (Reviewer) ---
# 이전단계 에이전트의 출력이 다음 에이전트의 입력이 됨
# 역할: 코드를 보고 개선점, 버그, 보안 문제를 지적
reviewer_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 까다로운 '전문 개발자'입니다. 신입 개발자가 짠 코드를 리뷰하세요. \n"
               "보안 취약점, 비효율적인 부분, 스타일 가이드를 점검하고 수정 제안을 하세요. \n"
               "코드가 완벽하다면 'PASS'라고만 답하세요."),
    ("user", "다음 코드를 리뷰해주세요:\n\n{code}")
])
reviewer_agent = reviewer_prompt | llm | StrOutputParser()

# --- Agent 1 (Refiner): 피드백 반영 ---
# 역할: 리뷰 내용을 바탕으로 코드 수정
refiner_prompt = ChatPromptTemplate.from_messages([
    ("system", "당신은 '신입 파이썬 개발자'입니다. 전문 개발자의 리뷰를 보고 코드를 수정해서 다시 제출하세요."),
    ("user", "이전 코드:\n{original_code}\n\n리뷰 내용:\n{feedback}\n\n위 내용을 반영하여 개선된 전체 코드를 다시 작성하세요.")
])
refiner_agent = refiner_prompt | llm | StrOutputParser()

def run_agent_collaboration(topic):
    print(f"목표: {topic}\n" + "="*50)

    # Round 1: 개발자가 초안 작성
    print("\n[신입 개발자] 코드 작성 중...")
    draft_code = developer_agent.invoke({"request": topic})
    print(f"---\n{draft_code[:200]}...\n(코드 생략)\n---")

    # Round 2: 리뷰어가 피드백 제공
    print("\n[전문 개발자] 코드 검토 중...")
    feedback = reviewer_agent.invoke({"code": draft_code})
    print(f"---\n{feedback}\n---")

    # 협업 판단: PASS가 아니면 수정 작업 진행
    if "PASS" not in feedback:
        print("\n[신입 개발자] 피드백 반영하여 수정 중...")
        final_code = refiner_agent.invoke({
            "original_code": draft_code,
            "feedback": feedback
        })
        
        print("\n[최종 결과물]")
        print(final_code)
    else:
        print("\n[최종 결과물]")
        print(draft_code)

if __name__ == "__main__":
    # 실행 예시
    run_agent_collaboration("사용자 비밀번호를 입력받아 DB에 저장하는 간단한 함수 (보안 고려)")