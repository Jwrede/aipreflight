"""A tiny RAG pipeline used to demonstrate aipreflight's rag profile.

Retrieval is keyword-overlap scoring over a small in-memory corpus. The generation
step calls an LLM to answer from the retrieved context and cites the source
document id. The real OpenAI call site stays in source so the cost gate (tokentoll)
can find and price the generation step. By default it runs offline: set
AIPREFLIGHT_FAKE_LLM=1, or simply run without OPENAI_API_KEY, and generation
returns the retrieved context verbatim, deterministic and with no network. When
nothing matches, the answerer abstains instead of making something up. That makes
two RAG failure modes observable without a real model: empty-retrieval handling
and hallucination on unanswerable questions.

Set AIPREFLIGHT_RAG_BROKEN=1 to simulate a retrieval regression (the retriever
returns an unrelated document). Answer quality and retrieval precision then drop,
which is exactly the case aipreflight's quality gate should catch even though the
service itself stays up.
"""

import os
import re

ABSTAIN = "I do not have enough information to answer that."

MODEL = "gpt-4o-mini"
PROVIDER = "openai"
PROMPT_VERSION = "v1"

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


def _fake_enabled() -> bool:
    return os.environ.get("AIPREFLIGHT_FAKE_LLM") == "1" or not os.environ.get("OPENAI_API_KEY")


def generate(query: str, context: str) -> str:
    """Generate an answer from retrieved context.

    Offline by default (returns the context verbatim, deterministic). The real
    OpenAI call site below stays in source so tokentoll can price the RAG
    generation step; set OPENAI_API_KEY to use it.
    """
    if _fake_enabled():
        return context

    from openai import OpenAI

    client = OpenAI()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Answer using only the provided context. Cite the source id in brackets."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ],
        max_tokens=256,
    )
    return resp.choices[0].message.content


def answer(query: str) -> dict:
    """Answer a query from retrieved context. Returns {answer, citations, retrieved}."""
    docs = retrieve(query)
    if not docs:
        return {"answer": ABSTAIN, "citations": [], "retrieved": []}
    top = docs[0]
    context = f"{top['text']} [{top['id']}]"
    return {
        "answer": generate(query, context),
        "citations": [top["id"]],
        "retrieved": [d["id"] for d in docs],
    }
