from fastapi.testclient import TestClient
from dev.app.main import app

# TestClient
# 서버를 켜지 않고도 요청/응답을 검증할 수 있게 해주는 테스트 도구
client = TestClient(app)

def test_read_item():
    response = client.get("/items/42")
    # 응답코드가 200이다
    assert response.status_code == 200
    # 응답결과는 다음과 같다
    assert response.json() == {"item_id": 42, "name": "Item 42"}