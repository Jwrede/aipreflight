"""Minimal hosted-API AI app: a FastAPI service that calls an LLM.

Run locally:
    pip install -r requirements.txt
    AIPREFLIGHT_FAKE_LLM=1 uvicorn app:app --reload   # offline, no API key
    # or set OPENAI_API_KEY to call the real API
"""

import logging

import llm
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="hosted-api-app")


class ChatRequest(BaseModel):
    prompt: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    return llm.complete(req.prompt)
