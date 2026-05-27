# hosted-api-app

A minimal hosted-API AI app used to demonstrate `aipreflight`'s `app` profile.
It is a FastAPI service with a single `/chat` endpoint that calls an LLM, plus
the production-readiness pieces an app profile checks for: a cost-priceable call
site, structured telemetry, an eval suite, and a rollback runbook.

## Run

```bash
pip install -r requirements.txt
AIPREFLIGHT_FAKE_LLM=1 uvicorn app:app --reload   # offline, no API key
curl -s localhost:8000/chat -d '{"prompt":"What is the capital of France?"}' -H 'content-type: application/json'
```

Set `OPENAI_API_KEY` (and unset `AIPREFLIGHT_FAKE_LLM`) to call the real API.

## Tests and evals (offline, deterministic)

```bash
pytest tests        # smoke tests via FastAPI TestClient
pytest evals        # answer-quality evals
```

## Check readiness

From the repo root:

```bash
aipreflight check --profile profiles/app.yml
```

This runs the cost gate (tokentoll scans the call site in `llm.py`), verifies the
telemetry contract in `observability.yml`, confirms the eval suite is configured,
and checks the rollback runbook exists.
