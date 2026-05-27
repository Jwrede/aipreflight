"""Smoke tests for the hosted-API app, against the FastAPI TestClient in fake mode."""

import os
import sys
from pathlib import Path

os.environ["AIPREFLIGHT_FAKE_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

import app as app_module  # noqa: E402

client = TestClient(app_module.app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_returns_answer_and_telemetry():
    resp = client.post("/chat", json={"prompt": "What is the capital of France?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "paris" in body["answer"].lower()
    for field in ("request_id", "model", "provider", "prompt_version", "input_tokens", "latency_ms"):
        assert field in body["telemetry"]
