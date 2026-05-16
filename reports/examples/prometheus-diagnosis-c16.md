# Inference Diagnosis

Generated: 2026-05-16 21:35 UTC
Probes analyzed: 240

## Client-Side Observations

- TTFT p50: 458ms, p95: 941ms
- Latency p50: 1.60s, p95: 3.11s
- Errors: 0/240 (0%)
- Degraded: 0/240 (0%)

## Server-Side Metrics

| Metric | Mean | Max | Unit |
|--------|------|-----|------|
| Server-reported TTFT p95 | 0.912 | 0.942 | seconds |
| Server-reported end-to-end latency p95 | 4.022 | 4.170 | seconds |
| Requests waiting in queue | 0.000 | 0.000 | count |
| Requests currently being processed | 13.500 | 16.000 | count |
| KV cache utilization | 0.017 | 0.021 | percent |
| Time spent waiting in queue p95 | 0.285 | 0.285 | seconds |

## Correlation Analysis

- Client and server TTFT p95 align (gap: 29ms). No significant network overhead.
- No significant issues detected in server metrics.

## Possible Causes

- No issues detected. Endpoint is healthy.

## Recommended Actions

- No action needed. Consider periodic monitoring with `llmprobe watch`.

