# Inference Diagnosis

Generated: 2026-05-16 20:33 UTC
Probes analyzed: 80

## Client-Side Observations

- TTFT p50: 529ms, p95: 1.15s
- Latency p50: 1.71s, p95: 3.27s
- Errors: 0/80 (0%)
- Degraded: 0/80 (0%)

## Server-Side Metrics

| Metric | Mean | Max | Unit |
|--------|------|-----|------|
| Server-reported TTFT p95 | 0.713 | 0.713 | seconds |
| Server-reported end-to-end latency p95 | 1.996 | 1.996 | seconds |
| Requests waiting in queue | 0.000 | 0.000 | count |
| Requests currently being processed | 0.000 | 0.000 | count |
| KV cache utilization | 0.000 | 0.000 | percent |
| Time spent waiting in queue p95 | 0.285 | 0.285 | seconds |

## Correlation Analysis

- Client and server TTFT align (gap: 184ms). No significant network overhead.
- No significant issues detected in server metrics.

## Possible Causes

- No issues detected. Endpoint is healthy.

## Recommended Actions

- No action needed. Consider periodic monitoring with `llmprobe watch`.

