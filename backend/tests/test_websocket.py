from fastapi.testclient import TestClient
from app.main import app


def test_websocket_connect_and_ping():
    with TestClient(app) as test_client:
        with test_client.websocket_connect("/ws/risk-events") as websocket:
            websocket.send_text("ping")
            data = websocket.receive_text()
            assert data == "pong"
