# Inference Readiness Report

Generated: 2026-05-16 18:27 UTC
Source: `fixtures/sample-probes.jsonl`
Total probes: 10

## Readiness Judgment

**DEGRADED**

Error rate 10%, degraded rate 20%. Investigate before serving production traffic.

## Endpoint Health

| Status | Count | Rate |
|--------|-------|------|
| healthy | 7 | 70% |
| degraded | 2 | 20% |
| error | 1 | 10% |

## Time to First Token (TTFT)

| Metric | Value |
|--------|-------|
| p50 | 295ms |
| p95 | 4.20s |
| p99 | 4.20s |
| min | 245ms |
| max | 4.20s |

## Latency

| Metric | Value |
|--------|-------|
| p50 | 3.40s |
| p95 | 11.20s |
| p99 | 11.20s |
| min | 3.10s |
| max | 11.20s |

## Throughput

| Metric | Value |
|--------|-------|
| p50 | 4.5 tok/s |
| p95 | 5.1 tok/s |
| min | 1.8 tok/s |
| max | 5.1 tok/s |

## Errors

- **Qwen/Qwen2-0.5B-Instruct**: connection refused

## Next Steps

- Monitor TTFT and latency trends under load.
- Add server-side metrics to correlate with queue depth and KV cache.
- Consider reducing concurrency or scaling resources.

