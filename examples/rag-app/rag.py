"""A tiny, fully offline RAG pipeline used to demonstrate aipreflight's rag profile.

There is no LLM and no network. Retrieval is keyword-overlap scoring over a small
in-memory corpus; answering is templated from the retrieved text and cites the
source document id. When nothing matches, the answerer abstains instead of making
something up. That makes two RAG failure modes observable without a real model:
empty-retrieval handling and hallucination on unanswerable questions.

Set AIPREFLIGHT_RAG_BROKEN=1 to simulate a retrieval regression (the retriever
returns an unrelated document). Answer quality and retrieval precision then drop,
which is exactly the case aipreflight's quality gate should catch even though the
service itself stays up.
"""

import os
import re

ABSTAIN = "I do not have enough information to answer that."

CORPUS = [
    {"id": "doc-geo-1", "title": "France", "text": "The capital of France is Paris."},
    {"id": "doc-sci-1", "title": "Water", "text": "Water boils at 100 degrees Celsius at sea level."},
    {"id": "doc-lang-1", "title": "Python", "text": "Python was created by Guido van Rossum."},
    {"id": "doc-sci-2", "title": "Light", "text": "The speed of light is about 299,792 kilometers per second."},
    {"id": "doc-geo-2", "title": "Japan", "text": "The capital of Japan is Tokyo."},
]

_STOP = {"the", "is", "of", "a", "what", "in", "at", "to", "how", "does", "do", "are"}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP}


def retrieve(query: str, top_k: int = 2) -> list[dict]:
    """Return the top_k documents by keyword overlap, dropping zero-overlap docs.

    An empty list means nothing relevant was found (the empty-retrieval case).
    """
    if os.environ.get("AIPREFLIGHT_RAG_BROKEN") == "1":
        # Simulate a broken retriever: always return the same unrelated document.
        return [CORPUS[-1]]

    q = _tokens(query)
    scored = []
    for doc in CORPUS:
        overlap = len(q & _tokens(doc["text"] + " " + doc["title"]))
        if overlap:
            scored.append((overlap, doc))
    scored.sort(key=lambda s: s[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


def answer(query: str) -> dict:
    """Answer a query from retrieved context. Returns {answer, citations, retrieved}."""
    docs = retrieve(query)
    if not docs:
        return {"answer": ABSTAIN, "citations": [], "retrieved": []}
    top = docs[0]
    return {
        "answer": f"{top['text']} [{top['id']}]",
        "citations": [top["id"]],
        "retrieved": [d["id"] for d in docs],
    }
