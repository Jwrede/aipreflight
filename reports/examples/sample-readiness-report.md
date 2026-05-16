# Inference Readiness Report

Generated: 2026-05-16 19:08 UTC
Source: `fixtures/sample-probes.jsonl`
Total probes: 10

## Verdict

**NOT READY**

Pass rate 70% below 95% threshold | TTFT p95 4.20s exceeds 500ms SLA | Latency p95 11.20s exceeds 10.00s SLA | Error rate 10% exceeds 1% threshold

## SLA Thresholds

| Metric | Threshold | Observed (p95) | Status |
|--------|-----------|----------------|--------|
| TTFT | 500ms | 4.20s | FAIL |
| Latency | 10.00s | 11.20s | FAIL |
| Throughput | >=3.0 tok/s | 4.5 tok/s | PASS |
| Error rate | <=1% | 10% | FAIL |

## Endpoint Health

| Status | Count | Rate |
|--------|-------|------|
| healthy | 7 | 70% |
| degraded | 2 | 20% |
| error | 1 | 10% |

## Time to First Token (TTFT)

| Percentile | Value |
|------------|-------|
| p50 | 295ms |
| p95 | 4.20s |
| p99 | 4.20s |

## Latency

| Percentile | Value |
|------------|-------|
| p50 | 3.40s |
| p95 | 11.20s |
| p99 | 11.20s |

## Throughput

| Percentile | Value |
|------------|-------|
| p50 | 4.5 tok/s |
| p95 | 5.1 tok/s |
| min | 1.8 tok/s |

## Errors

- **Qwen/Qwen2-0.5B-Instruct**: connection refused

## Next Steps

- Do not route production traffic.
- Run `python3 scripts/diagnose.py <probes.jsonl>` to correlate with server metrics.
- Check: model loading status, resource limits, network path.

