# Concurrency Sweep Comparison

| Concurrency | TTFT p50 | TTFT p95 | Latency p50 | Latency p95 | Throughput p50 | Error Rate |
|-------------|----------|----------|-------------|-------------|----------------|------------|
| 1 | 77ms | 161ms | 96ms | 178ms | 528.1 tok/s | 0% |
| 2 | 80ms | 213ms | 102ms | 236ms | 432.7 tok/s | 0% |
| 4 | 73ms | 212ms | 95ms | 236ms | 465.0 tok/s | 0% |
| 8 | 76ms | 211ms | 100ms | 236ms | 405.9 tok/s | 0% |
| 16 | 71ms | 431ms | 97ms | 455ms | 379.6 tok/s | 0% |
| 32 | 46ms | 728ms | 70ms | 754ms | 450.2 tok/s | 0% |

## Observations

- TTFT p95 increased 4.5x from concurrency 1 to 32. Likely saturating compute or hitting queue backpressure.

