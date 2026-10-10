"""Smoke test: proves every mode works end to end (uses LLM_MOCK, so no API key needed).

Run before the event:  uv run pytest -q
"""
import os

os.environ["LLM_MOCK"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _sample():
    r = client.post("/api/sample")
    assert r.status_code == 200, r.text
    return r.json()["dataset_id"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_sample_profile():
    r = client.post("/api/sample")
    body = r.json()
    assert body["profile"]["rows"] == 240
    assert any(c["missing"] > 0 for c in body["profile"]["column_info"])


def test_analyze():
    ds = _sample()
    r = client.post("/api/run", json={"mode": "analyze", "input": "summarize the numbers", "dataset_id": ds})
    assert r.status_code == 200, r.text
    assert r.json()["table"]["columns"]


def test_docs():
    _sample()
    r = client.post("/api/run", json={"mode": "docs", "input": "What is the refund policy?"})
    assert r.status_code == 200, r.text
    assert r.json()["sources"]


def test_extract_and_classify():
    r = client.post("/api/run", json={"mode": "extract", "input": "Ali from Acme met Sara in Lahore on 3 May.", "options": {"fields": "people, locations"}})
    assert r.status_code == 200 and r.json()["table"]["rows"]
    r = client.post("/api/run", json={"mode": "classify", "input": "My parcel is late", "options": {"labels": "billing, delivery, technical"}})
    assert r.status_code == 200 and r.json()["metrics"]["label"] == "billing"  # mock always picks the first label
    ds = _sample()
    r = client.post("/api/run", json={"mode": "classify", "dataset_id": ds, "options": {"column": "message", "labels": "billing, delivery"}})
    assert r.status_code == 200 and len(r.json()["table"]["rows"]) == 10


def test_predict():
    ds = _sample()
    r = client.post("/api/run", json={"mode": "predict", "dataset_id": ds, "options": {"target": "resolved"}})
    assert r.status_code == 200, r.text
    assert "accuracy" in r.json()["metrics"]


def test_custom_and_chat():
    r = client.post("/api/run", json={"mode": "custom", "input": "hello"})
    assert r.status_code == 200
    r = client.post("/api/chat", json={"message": "hi", "history": []})
    assert r.status_code == 200 and r.json()["reply"]


def test_friendly_errors():
    r = client.post("/api/run", json={"mode": "analyze", "input": "x"})
    assert r.status_code == 400 and "dataset" in r.json()["detail"].lower()
