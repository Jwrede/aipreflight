# Runbook: Roll back an AI feature

Use this when a shipped change (prompt, model, provider, or retrieval config)
degrades quality, cost, or latency in production.

## When to roll back

- Answer quality regressed (eval pass rate dropped, user complaints spiked).
- Cost per request or monthly spend jumped after a model or prompt change.
- Latency or error rate breached SLA after a routing change.

## What to roll back

AI features have several independently versioned surfaces. Identify which one changed:

| Surface | Rollback action |
|---------|-----------------|
| Prompt | Revert `prompt_version` to the previous value and redeploy. |
| Model | Point the model/provider config back to the prior model. |
| Provider routing | Restore the previous routing weights or pin to the known-good provider. |
| Retrieval config | Revert the index, chunking, or top-k settings (RAG). |

## Steps

1. Identify the bad change from the deploy log and the `prompt_version` / `model`
   fields in telemetry (see `observability.yml`).
2. Revert the relevant config and redeploy, or shift traffic back to the previous
   revision.
3. Re-run the readiness gate before restoring full traffic:
   ```bash
   aipreflight check --profile profiles/app.yml
   ```
4. Confirm cost, latency, and eval checks pass, then ramp traffic back up.

## Prevention

Run `aipreflight check` in CI before merging prompt, model, or retrieval changes
so regressions are caught before they reach production traffic.
