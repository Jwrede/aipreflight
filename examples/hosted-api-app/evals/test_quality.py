"""Answer-quality evals for the hosted-API app.

Deterministic and offline: forces fake-LLM mode so it runs in CI with no API key.
aipreflight's app profile checks that this suite is configured; Phase 4 wires it
into a quality gate.
"""

import os
import sys
from pathlib import Path

os.environ["AIPREFLIGHT_FAKE_LLM"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import llm  # noqa: E402

CASES = [
    ("What is the capital of France?", "paris"),
    ("What is 2+2?", "4"),
]

MIN_PASS_RATE = 0.9


def test_answer_quality():
    passed = sum(1 for q, expected in CASES if expected in llm.complete(q)["answer"].lower())
    assert passed / len(CASES) >= MIN_PASS_RATE
