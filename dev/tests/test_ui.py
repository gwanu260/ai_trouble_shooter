from streamlit.testing.v1 import AppTest
from unittest.mock import MagicMock, patch

# requests.get을 Mocking하여 실제 HTTP 요청을 보내지 않음
# 모킹:테스트를 위해 실제 객체나 외부 서비스 대신 가짜(모조품) 객체를 만들어 사용하는 것
@patch("requests.get")
def test_ui_search_success(mock_get):
    # 1. API 응답 가짜 데이터(Mock) 설정
    #    서버가 꺼져 있어도 테스트 통과 가능
    mock_response               = MagicMock()
    mock_response.status_code   = 200
    mock_response.json.return_value = {"item_id": 10, "name": "Item 10"}
    mock_get.return_value       = mock_response

    # 2. Streamlit 앱 로드 (ui.py 경로 지정)
    at = AppTest.from_file("ui.py")
    at.run()

    # 3. 사용자 인터랙션 시뮬레이션
    at.number_input[0].set_value(10).run() # 숫자 입력
    at.button[0].click().run()             # 버튼 클릭

    # 4. 결과 검증 (성공 메시지가 떴는지 확인)
    assert at.success[0].value == "Found: Item 10"