"""RAG quality evals for the tiny offline pipeline. Emits aipreflight eval JSON.

Run directly to print the result JSON that aipreflight's rag profile gates on:

    python examples/rag-app/evals/run_evals.py

Reports overall pass rate plus the RAG-specific metrics aipreflight cares about:
retrieval precision, answer quality, citation rate, hallucination rate, and
empty-retrieval handling. Deterministic and offline, so it runs in CI.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rag  # noqa: E402

# Labeled queries. answerable cases have a gold document and an expected substring;
# the unanswerable case must be abstained on, not answered.
CASES = [
    {"q": "What is the capital of France?", "gold": "doc-geo-1", "expect": "paris", "answerable": True},
    {"q": "At what temperature does water boil?", "gold": "doc-sci-1", "expect": "100", "answerable": True},
    {"q": "Who created Python?", "gold": "doc-lang-1", "expect": "guido", "answerable": True},
    {"q": "What is the capital of Japan?", "gold": "doc-geo-2", "expect": "tokyo", "answerable": True},
    {"q": "What is the GDP of Mars in 1850?", "gold": None, "expect": None, "answerable": False},
]


def main() -> None:
    answerable = [c for c in CASES if c["answerable"]]
    unanswerable = [c for c in CASES if not c["answerable"]]

    retrieval_hits = 0
    answer_hits = 0
    citation_hits = 0
    passed = 0

    for c in answerable:
        result = rag.answer(c["q"])
        retrieved = result["retrieved"]
        ans = result["answer"].lower()
        retrieval_ok = bool(retrieved) and retrieved[0] == c["gold"]
        answer_ok = c["expect"] in ans
        cited = bool(result["citations"])
        retrieval_hits += retrieval_ok
        answer_hits += answer_ok
        citation_hits += cited
        passed += answer_ok

    hallucinated = 0
    empty_handled = 0
    for c in unanswerable:
        result = rag.answer(c["q"])
        abstained = result["answer"] == rag.ABSTAIN
        hallucinated += 0 if abstained else 1
        empty_handled += 1 if abstained else 0
        passed += 1 if abstained else 0

    n_ans = len(answerable) or 1
    n_unans = len(unanswerable) or 1
    total = len(CASES)

    out = {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4),
        "metrics": {
            "retrieval_precision": round(retrieval_hits / n_ans, 4),
            "answer_quality": round(answer_hits / n_ans, 4),
            "citation_rate": round(citation_hits / n_ans, 4),
            "hallucination_rate": round(hallucinated / n_unans, 4),
            "empty_retrieval_handled": round(empty_handled / n_unans, 4),
        },
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
