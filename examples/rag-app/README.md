# RAG example app

A tiny, fully offline retrieval-augmented generation pipeline used to demonstrate
aipreflight's `rag` profile. No LLM, no network, no API key.

- `rag.py` - keyword-overlap retriever over a 5-document in-memory corpus, plus a
  templated answerer that cites its source document and abstains when nothing
  relevant is retrieved.
- `evals/run_evals.py` - labeled queries that produce the RAG quality metrics
  aipreflight gates on, emitted as JSON.
- `observability.yml` - the telemetry fields the app declares per query.

## Why this exists

A RAG system can be "up" while being unsafe to ship: retrieval regressed, answers
stopped citing sources, or the model began answering unanswerable questions.
Infrastructure checks miss all of that. This example makes those failure modes
reproducible so the readiness gate has something real to catch.

## Run the evals directly

```bash
python examples/rag-app/evals/run_evals.py
```

## Run the readiness gate

```bash
# Healthy: retrieval, answers, and citations all within gate -> PASS
aipreflight check --profile profiles/rag.yml

# Simulate a retrieval regression -> retrieval precision and answer quality drop,
# the unanswerable query gets hallucinated, and readiness FAILs while the
# observability and rollback checks still pass.
AIPREFLIGHT_RAG_BROKEN=1 aipreflight check --profile profiles/rag.yml
```

This is the point the example proves: bad retrieval fails readiness even though
the service itself never went down.
