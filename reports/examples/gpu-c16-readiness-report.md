# Inference Readiness Report

Generated: 2026-05-17 14:27 UTC
Source: `runs/sweep-20260517T142332/c16/llmprobe.jsonl`
Total probes: 240

## Verdict

**READY**

All SLA thresholds met. Safe to route traffic.

## SLA Thresholds

| Metric | Threshold | Observed (p95) | Status |
|--------|-----------|----------------|--------|
| TTFT | 500ms | 431ms | PASS |
| Latency | 10.00s | 455ms | PASS |
| Throughput | >=3.0 tok/s | 379.6 tok/s | PASS |
| Error rate | <=1% | 0% | PASS |

## Endpoint Health

| Status | Count | Rate |
|--------|-------|------|
| healthy | 240 | 100% |
| degraded | 0 | 0% |
| error | 0 | 0% |

## Time to First Token (TTFT)

| Percentile | Value |
|------------|-------|
| p50 | 71ms |
| p95 | 431ms |
| p99 | 506ms |

## Latency

| Percentile | Value |
|------------|-------|
| p50 | 97ms |
| p95 | 455ms |
| p99 | 533ms |

## Throughput

| Percentile | Value |
|------------|-------|
| p50 | 379.6 tok/s |
| p95 | 469.7 tok/s |
| min | 112.2 tok/s |

## Next Steps

- Endpoint is healthy. No immediate action needed.
- Consider running `scripts/diagnose.py` with Prometheus for deeper visibility.

