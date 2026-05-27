"""LLM client wrapper with structured telemetry and an offline fake mode.

Every call emits a structured record with the observability fields aipreflight's
app profile expects (request_id, model, provider, prompt_version, token counts,
latency, cost, error type). The real OpenAI call site stays in source so cost
tooling (tokentoll) can find and price it. Set AIPREFLIGHT_FAKE_LLM=1 (or simply
run without OPENAI_API_KEY) to use deterministic canned answers with no network.
"""

import json
import logging
import os
import time
import uuid

MODEL = "gpt-4o-mini"
PROVIDER = "openai"
PROMPT_VERSION = "v1"

logger = logging.getLogger("hosted_api_app")

_FAKE_ANSWERS = {
    "capital of france": "The capital of France is Paris.",
    "2+2": "2 + 2 = 4.",
    "2 + 2": "2 + 2 = 4.",
}


def _fake_enabled() -> bool:
    return os.environ.get("AIPREFLIGHT_FAKE_LLM") == "1" or not os.environ.get("OPENAI_API_KEY")


def _fake_answer(prompt: str) -> str:
    p = prompt.lower()
    for key, answer in _FAKE_ANSWERS.items():
        if key in p:
            return answer
    return "I do not have enough information to answer that."


def complete(prompt: str) -> dict:
    """Answer a prompt and return {answer, telemetry}."""
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    error_type = None

    if _fake_enabled():
        answer = _fake_answer(prompt)
        input_tokens, output_tokens = len(prompt.split()), len(answer.split())
    else:
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )
        answer = resp.choices[0].message.content
        input_tokens = resp.usage.prompt_tokens
        output_tokens = resp.usage.completion_tokens

    telemetry = {
        "request_id": request_id,
        "model": MODEL,
        "provider": PROVIDER,
        "prompt_version": PROMPT_VERSION,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        "cost_usd": None,
        "error_type": error_type,
    }
    logger.info(json.dumps(telemetry))
    return {"answer": answer, "telemetry": telemetry}
