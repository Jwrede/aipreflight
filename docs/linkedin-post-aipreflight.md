# LinkedIn draft: aipreflight

Normal software has CI gates, smoke tests, canaries, and SLOs.

Classical ML has model validation, drift monitoring, and model blessing.

Modern AI apps often still ship prompt changes, RAG changes, model/provider changes, and AI features without equivalent preflight checks.

That is the gap I have been working on with `aipreflight`.

`aipreflight` is a CI/CD readiness gate for AI applications. It checks:

- eval quality
- RAG behavior
- token/cost budgets
- latency and errors
- observability fields
- rollback/runbook readiness

The goal is simple:

```text
one command
one readiness report
one ship/block verdict
```

This is not meant to replace Grafana, OpenTelemetry, Kubernetes, LiteLLM, or eval frameworks. It sits at the release boundary and turns their signals into a deployment decision.

I wrote up the positioning here:

https://jonathanwrede.de/en/blog/the-missing-deployment-gate-for-ai-applications/

Repo:

https://github.com/Jwrede/aipreflight

