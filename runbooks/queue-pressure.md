# Runbook: Queue Pressure

## Symptom

Prometheus shows `vllm:num_requests_waiting` > 5. Diagnose.py reports "Queue pressure" in correlation analysis.

## Diagnosis steps

1. Confirm queue depth during load:

```bash
python3 scripts/diagnose.py runs/latest/llmprobe.jsonl --prometheus http://localhost:9090
```

Look for: "Queue pressure: Max queue depth N."

2. Check if queue time correlates with TTFT:

Queue time p95 in server metrics should be close to (client TTFT - server TTFT).
If queue time is high but server TTFT is low, requests wait before processing starts.

## Common causes

| Cause | Evidence | Fix |
|-------|----------|-----|
| Too many concurrent requests | Queue grows with concurrency | Limit upstream concurrency |
| Slow model | Queue grows even at low concurrency | Use faster model or add GPU |
| max_num_seqs too low | Queue grows while running < max_num_seqs | Increase max_num_seqs |
| Long-running requests | Few running requests but queue grows | Set request timeout |

## Resolution

- Reduce incoming concurrency via load balancer or rate limiter
- Increase `--max-num-seqs` if memory allows
- Scale horizontally (add replicas behind load balancer)
- Set `--max-num-batched-tokens` higher if KV cache can handle it
- Add request timeout to prevent long-tail requests from blocking slots
