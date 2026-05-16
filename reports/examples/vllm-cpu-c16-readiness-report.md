# Inference Readiness Report

Generated: 2026-05-16 19:58 UTC
Source: `runs/sweep-20260516T195711/c16/llmprobe.jsonl`
Total probes: 80

## Verdict

**NOT READY**

TTFT p95 630ms exceeds 500ms SLA

## SLA Thresholds

| Metric | Threshold | Observed (p95) | Status |
|--------|-----------|----------------|--------|
| TTFT | 500ms | 630ms | FAIL |
| Latency | 10.00s | 2.32s | PASS |
| Throughput | >=3.0 tok/s | 10.7 tok/s | PASS |
| Error rate | <=1% | 0% | PASS |

## Endpoint Health

| Status | Count | Rate |
|--------|-------|------|
| healthy | 80 | 100% |
| degraded | 0 | 0% |
| error | 0 | 0% |

## Time to First Token (TTFT)

| Percentile | Value |
|------------|-------|
| p50 | 591ms |
| p95 | 630ms |
| p99 | 634ms |

## Latency

| Percentile | Value |
|------------|-------|
| p50 | 1.54s |
| p95 | 2.32s |
| p99 | 2.39s |

## Throughput

| Percentile | Value |
|------------|-------|
| p50 | 10.7 tok/s |
| p95 | 13.9 tok/s |
| min | 7.0 tok/s |

## Next Steps

- Do not route production traffic.
- Run `python3 scripts/diagnose.py <probes.jsonl>` to correlate with server metrics.
- Check: model loading status, resource limits, network path.

