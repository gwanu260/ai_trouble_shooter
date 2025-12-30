'''
- 특징
    - LangGraph를 사용한 코드는 **"순환(Cycle)"과 "상태 유지(State Persistence)"**가 핵심
    - 단순히 A가 B에게 넘기는 것이 아니라, 결과가 만족스러울 때까지 A와 B가 서로 주고받는 무한 루프를 만들 수 있음  
    - 이번 시나리오는 **[코드 작성자 ↔ 코드 리뷰어]**의 무한 개선 루프임
- 구성
    - 작성자: 코드를 작성
    - 리뷰어: 코드를 평가
    - 불합격(Fail): 피드백과 함께 다시 작성자에게 보냄 (Loop)
    - 합격(Pass): 프로세스를 종료 (End)
- 아키텍처
    - LangGraph 아키텍처 다이어그램
    - State: 현재 대화 내용과 수정 횟수를 저장하는 공유 메모리
    - Coder Node: 상태를 읽어 코드를 생성/수정
    - Reviewer Node: 코드를 검증하고 Pass/Fail 판정
    - Conditional Edge: Reviewer의 판정에 따라 Coder로 돌아갈지 End로 갈지 결정
- 설치
    - pip install langchain_aws langchain_core langgraph
'''
import operator
from typing import Annotated, List, TypedDict, Union
from langchain_aws import ChatBedrock
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import dotenv
dotenv.load_dotenv()

# --- 1. 상태(State) 정의 ---
# 그래프 안에서 노드끼리 주고받을 "공유 메모리" 구조입니다.
# messages: 대화 기록 (계속 누적됨)
# iterations: 루프가 무한히 돌지 않게 제어하는 카운터
class AgentState(TypedDict):
    # 이 변수(messages)에 새로운 값이 들어오면, 기존 값을 지우지 말고 덧셈(+)해서 뒤에 이어 붙여라!
    # List[BaseMessage] (데이터 타입)
        # 이 변수에는 BaseMessage 객체들의 리스트가 들어간다는 뜻
        # BaseMessage는 HumanMessage(사람), AIMessage(봇), SystemMessage(설정) 등의 부모 클래스
        # 이곳은 대화 기록이 저장되는 리스트다
    # operator.add (리듀서 / 업데이트 함수)
        # 파이썬의 표준 라이브러리인 operator 모듈의 덧셈 함수
        # 파이썬에서 리스트끼리 더하면(+) **이어 붙이기(Concatenation)**가 됩니다.
        # [A] + [B] = [A, B]
        # 새 데이터가 들어왔을 때, 옛날 데이터와 어떻게 합칠까?"에 대한 규칙
    # Annotated[...] (메타데이터 표기)
        # 타입 힌트에 추가 정보를 담는 데 사용
        # 여기서는 operator.add를 추가로 전달하여 상태 업데이트 방식을 지정
        # 그냥 선언했다면 LangGraph는 기본적으로 **"덮어쓰기(Overwrite)"**를 수행 -> 기억상실
        # 대화의 기억을 관리하는 법 설정
    messages: Annotated[List[BaseMessage], operator.add]
    # 재시도 횟수 -> 오류발생 혹은 리뷰 후 수정에 대한 최대 순환 횟수 체크 가능
    iterations: int

# --- 2. LLM 설정 (Bedrock) ---
llm = ChatBedrock(
    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
    region="ap-northeast-1",
    client=None, # boto3 client 자동 생성
    model_kwargs={"temperature": 0.5}
)

# --- 3. 노드(Node) 정의 ---

# [Node 1] 작성자 (Coder)
def coder_node(state: AgentState):
    print("\n--- [Coder] 작업 중 ---")
    # 1. 메세지 추출 (프롬ㅍ트 획득)
    messages = state['messages']
    
    # 시스템 메시지: 개발자 페르소나
    coder_prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 초보 Python 개발자입니다. 요청사항에 맞는 코드를 작성하세요. "
                   "리뷰어의 피드백이 있다면 그것을 반영해서 코드를 수정하세요."),
        ("placeholder", "{messages}")
    ])
    # 프롬프트 -> llm으로 랭체인 연결
    chain = coder_prompt | llm
    # llm 호출 통해서 추론 행위 진행 => 코드 작성
    response = chain.invoke({"messages": messages})
    
    # 상태 업데이트: 반복 횟수 +1, 새 메시지 추가
    return {
        # 응답된 내용이 추가되서 대화 내용이 구성
        "messages": [response], 
        # 코드가 작성된 횟수 +1 증가 기존값(반복횟수) + 1
        "iterations": state.get("iterations", 0) + 1
    }

# [Node 2] 리뷰어 (Reviewer)
def reviewer_node(state: AgentState):
    print("\n--- [Reviewer] 검토 중 ---")
    messages = state['messages']
    # 바로 직전에 작성된 메세지가 코드 
    last_message = messages[-1] # 방금 Coder가 짠 코드
    
    # 시스템 메시지: 리뷰어 페르소나
    # 핵심: 만족하면 'PASS', 아니면 'FAIL'과 피드백을 주도록 지시
    reviewer_prompt = ChatPromptTemplate.from_messages([
        ("system", "당신은 전문 코드 리뷰어입니다. 아래 코드를 엄격하게 검사하세요.\n"
                   "코드가 완벽하고 보안 문제가 없다면 반드시 첫 줄에 'PASS'라고 적으세요.\n"
                   "문제가 있다면 첫 줄에 'FAIL'이라고 적고 구체적인 수정 지시사항을 남기세요."),
        ("human", "다음 코드를 리뷰해주세요:\n{code}")
    ])
    # 랭체인으로 연결
    chain = reviewer_prompt | llm
    # 이전에 작성된 코드를 삽입해서 프롬프트 구성하여 llm 호출
    response = chain.invoke({"code": last_message.content})
    # 반복횟수 증가 x , 코드를 새로 작성할때만 증가
    # 상태 내부에 메세지만 갱신(필요한것만 갱신)
    return {"messages": [response]}

# --- 4. 엣지(Edge) 로직 정의 ---

# 조건부 엣지 함수: Reviewer의 응답을 보고 다음 경로 결정
def should_continue(state: AgentState):
    messages = state['messages']
    # 최종 메세지 획득 -> 리뷰어의 응답나옴
    last_message = messages[-1].content
    # 상태에 존재하는 최종 시도 횟수 획득
    iterations = state['iterations']
    
    # 1. 안전장치: 최대 3번까지만 수정 (무한 루프 방지)
    if iterations >= 3:
        print("--- [System] 최대 반복 횟수 도달. 종료합니다. ---")
        return "end"
    
    # 2. 리뷰 통과 여부 확인
    if "PASS" in last_message:
        print("--- [System] 리뷰 통과! (PASS) ---")
        return "end"
    else:
        print("--- [System] 리뷰 거절. 다시 작성자에게 보냅니다. (FAIL) ---")
        return "continue"

# --- 5. 그래프(Graph) 구성 ---

workflow = StateGraph(AgentState)

# 노드 등록
workflow.add_node("coder", coder_node)       # 최초 작성 : 코드 작성자 에이전트(노드 역할 담당)
workflow.add_node("reviewer", reviewer_node) # 리뷰어 에이전트 (노드 역할)

# 흐름 연결
# 시작 -> Coder
workflow.set_entry_point("coder")            # 시작점 지정

# Coder -> Reviewer (무조건 이동)
workflow.add_edge("coder", "reviewer")       # 기본 방향 설정

# Reviewer -> (조건부 분기)                    
workflow.add_conditional_edges(
    "reviewer",
    should_continue,                         # 함수에서 체크가 일어남
                                             # 다시 코더로 갈지, 끝낼지
    {
        "continue": "coder", # FAIL이면 다시 coder로
        # 신입 개발자 에이전트가 계속 피드배 받으면서 코드를 발전시킬 수 있음 에이전트ㅅ
        "end": END           # PASS면 종료ㅡ END면 조건부 함수의 반환값을 END OR CONTINUE로 설정
    }
)

# 컴파일 (실행 가능한 앱으로 변환)
app = workflow.compile()

# --- 6. 실행 ---

if __name__ == "__main__":
    # 초기 질문
    # 비효율적으로 작성 -> 임의로 설정 -> 순환시키기 위해서 오류가 있거나, 비효율적 코드를 지정, 실제로는 x 
    initial_input = "리스트에서 중복을 제거하고 정렬하는 파이썬 함수를 만들어줘. 근데 좀 비효율적으로 작성해줘."
    # 랭그래프의 상태가 달라서 상태 구조에 맞게 구성 (메세지, 순환횟수(초기값은 0))
    # 형식이 안 맞으면 오류 발생 => TypedDict로 지정해둬서 구조를 지켜야함 (fastapi pydantic 참고)
    inputs = {
        "messages": [HumanMessage(content=initial_input)],
        "iterations": 0
    }
    
    print(f"🚀 시작 요청: {initial_input}")
    
    # 그래프 실행 (스트리밍 방식으로 진행 상황 확인)
    for output in app.stream(inputs):
        print(output) # 과정 확인 
        pass # 내부 print 문으로 로그 확인

    print("\n✅ 최종 완료")