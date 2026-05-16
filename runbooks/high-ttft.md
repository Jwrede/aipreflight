# Runbook: High TTFT

## Symptom

TTFT p95 exceeds SLA threshold. Gate reports FAIL with TTFT violation.

## Diagnosis steps

1. Check if the problem is network or compute:

```bash
python3 scripts/diagnose.py runs/latest/llmprobe.jsonl --prometheus http://localhost:9090
```

If client TTFT >> server TTFT (gap > 100ms): problem is network/proxy.
If client TTFT ~= server TTFT: problem is inference compute.

2. Check concurrency level:

```bash
./scripts/sweep.sh configs/llmprobe/vllm.yml 1,2,4,8
```

If TTFT is fine at c1 but breaks at cN: server is saturated at N concurrent users.

## Common causes

| Cause | Evidence | Fix |
|-------|----------|-----|
| CPU saturation | TTFT scales linearly with concurrency | Add replicas or limit concurrency |
| Long prompts | TTFT spikes on specific requests | Reduce max_model_len or use prefix caching |
| Cold start | First few probes slow, rest normal | Pre-warm model with dummy requests |
| Proxy overhead | Client/server TTFT gap > 100ms | Check TLS termination, DNS, load balancer |
| Batch contention | Queue depth > 0 during probes | Reduce max_num_seqs or scale out |

## Resolution

For compute-bound TTFT at high concurrency:
- Reduce `--max-num-seqs` to limit batch size
- Add GPU or more CPU cores
- Use a smaller or quantized model
- Enable prefix caching (`--enable-prefix-caching`)

For network-bound TTFT:
- Bypass unnecessary proxy layers for health checks
- Move probe client closer to the endpoint
- Check for DNS resolution delays
