"""Test ở chế độ mock: không cần API key, không cần Supabase.

Chạy từ thư mục backend/:  pytest -q
"""
import os

os.environ["LLM_PROVIDER"] = "mock"
os.environ["RETRIEVER"] = "mock"
os.environ["MIN_SECONDS_BETWEEN_QUESTIONS"] = "0"
os.environ["SUPABASE_URL"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_chat_json_has_sources():
    r = client.post("/api/chat?stream=false", json={"message": "Đăng ký học phần bổ sung thế nào?", "session_id": "t1"})
    assert r.status_code == 200
    body = r.json()
    assert body["refused"] is False
    assert len(body["sources"]) >= 1
    assert body["sources"][0]["n"] == 1


def test_chat_out_of_scope_is_refused():
    r = client.post("/api/chat?stream=false", json={"message": "Công thức nấu phở bò", "session_id": "t2"})
    assert r.json()["refused"] is True


def test_chat_stream_events_in_order():
    with client.stream("POST", "/api/chat", json={"message": "Học phí tính theo tín chỉ thế nào?", "session_id": "t3"}) as r:
        text = "".join(r.iter_text())
    assert text.index("event: token") < text.index("event: sources") < text.index("event: done")


def test_invalid_input():
    r = client.post("/api/chat?stream=false", json={"message": ""})
    assert r.status_code == 422


def test_feedback():
    r = client.post("/api/feedback", json={"answer_id": "abc", "rating": 1})
    assert r.json() == {"ok": True}
