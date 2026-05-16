# Cross-Engine Comparison: vLLM vs Ollama on CPU

Hardware: 8 vCPUs, 16GB RAM, x86_64 (no GPU)
Model: Qwen2 0.5B (float32 on vLLM, Q4 quantized on Ollama)
Test: 5 probes per concurrency level, 3s interval

## vLLM (float32, continuous batching)

| Concurrency | TTFT p50 | TTFT p95 | Latency p50 | Throughput p50 | Error Rate |
|-------------|----------|----------|-------------|----------------|------------|
| 1 | 110ms | 122ms | 731ms | 16.4 tok/s | 0% |
| 2 | 138ms | 209ms | 764ms | 18.6 tok/s | 0% |
| 4 | 225ms | 279ms | 821ms | 17.5 tok/s | 0% |
| 8 | 327ms | 380ms | 989ms | 15.4 tok/s | 0% |
| 16 | 591ms | 630ms | 1.54s | 10.7 tok/s | 0% |

## Ollama (Q4 quantized, llama.cpp backend)

| Concurrency | TTFT p50 | TTFT p95 | Latency p50 | Throughput p50 | Error Rate |
|-------------|----------|----------|-------------|----------------|------------|
| 1 | 204ms | 551ms | 619ms | 42.3 tok/s | 0% |
| 2 | 622ms | 948ms | 1.01s | 47.3 tok/s | 0% |
| 4 | 750ms | 1.45s | 1.11s | 59.3 tok/s | 0% |
| 8 | 2.50s | 13.35s | 2.94s | 51.8 tok/s | 0% |
| 16 | 6.90s | 12.08s | 7.26s | 53.1 tok/s | 0% |

## Key Observations

1. **Throughput**: Ollama is 3-4x faster per-token (42 vs 16 tok/s at c1) due to Q4 quantization
   and llama.cpp's CPU-optimized kernels.

2. **TTFT under load**: vLLM degrades gracefully (110ms to 591ms at c16). Ollama collapses
   (204ms to 6.9s at c16). vLLM's continuous batching keeps TTFT low even at high concurrency.

3. **The tradeoff**: Ollama wins on raw throughput. vLLM wins on latency stability under load.
   For interactive use (chatbots, code completion) where TTFT matters, vLLM is better at
   concurrency > 4. For batch workloads where total throughput matters, Ollama wins.

4. **SLA compliance (500ms TTFT threshold)**:
   - vLLM: passes up to concurrency 8, fails at 16
   - Ollama: passes at concurrency 1 only, fails at 2+

## Verdict

For a 500ms TTFT SLA on this hardware:
- vLLM supports 8 concurrent users
- Ollama supports 1 concurrent user

Choose vLLM for serving, Ollama for local development and batch inference.
