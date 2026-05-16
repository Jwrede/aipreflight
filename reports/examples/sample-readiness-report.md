# Inference Readiness Report

Generated: 2026-05-16 19:58 UTC
Source: `runs/sweep-20260516T195711/c1/llmprobe.jsonl`
Total probes: 5

## Verdict

**READY**

All SLA thresholds met. Safe to route traffic.

## SLA Thresholds

| Metric | Threshold | Observed (p95) | Status |
|--------|-----------|----------------|--------|
| TTFT | 500ms | 122ms | PASS |
| Latency | 10.00s | 1.87s | PASS |
| Throughput | >=3.0 tok/s | 16.4 tok/s | PASS |
| Error rate | <=1% | 0% | PASS |

## Endpoint Health

| Status | Count | Rate |
|--------|-------|------|
| healthy | 5 | 100% |
| degraded | 0 | 0% |
| error | 0 | 0% |

## Time to First Token (TTFT)

| Percentile | Value |
|------------|-------|
| p50 | 110ms |
| p95 | 122ms |
| p99 | 122ms |

## Latency

| Percentile | Value |
|------------|-------|
| p50 | 731ms |
| p95 | 1.87s |
| p99 | 1.87s |

## Throughput

| Percentile | Value |
|------------|-------|
| p50 | 16.4 tok/s |
| p95 | 23.0 tok/s |
| min | 11.4 tok/s |

## Next Steps

- Endpoint is healthy. No immediate action needed.
- Consider running `scripts/diagnose.py` with Prometheus for deeper visibility.

