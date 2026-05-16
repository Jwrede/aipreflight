# Concurrency Sweep Comparison

| Concurrency | TTFT p50 | TTFT p95 | Latency p50 | Latency p95 | Throughput p50 | Error Rate |
|-------------|----------|----------|-------------|-------------|----------------|------------|
| 1 | 110ms | 122ms | 731ms | 1.87s | 16.4 tok/s | 0% |
| 2 | 138ms | 209ms | 764ms | 1.41s | 18.6 tok/s | 0% |
| 4 | 225ms | 279ms | 821ms | 1.43s | 17.5 tok/s | 0% |
| 8 | 327ms | 380ms | 989ms | 1.63s | 15.4 tok/s | 0% |
| 16 | 591ms | 630ms | 1.54s | 2.32s | 10.7 tok/s | 0% |

## Observations

- TTFT p95 increased 5.2x from concurrency 1 to 16. Likely saturating compute or hitting queue backpressure.

