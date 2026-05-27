"""Answer-quality evals for the hosted-API app. Emits aipreflight eval JSON.

Run directly to print the result JSON that aipreflight's app profile gates on:

    python examples/hosted-api-app/evals/run_evals.py

Deterministic and offline: forces fake-LLM mode so it runs in CI with no API key.
The same cases are asserted by test_quality.py for a plain pytest run; this script
turns them into the pass-rate and answer-quality numbers aipreflight gates on.
"""

import json
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


def main() -> None:
    passed = sum(1 for q, expected in CASES if expected in llm.complete(q)["answer"].lower())
    total = len(CASES)
    out = {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4),
        "metrics": {
            "answer_quality": round(passed / total, 4),
        },
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
