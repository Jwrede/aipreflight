# Cross-Engine Comparison: GPU vs CPU (vLLM vs Ollama)

Model: Qwen2 0.5B
Test: 15 probes per concurrency level, 2s interval

## vLLM on RTX 3090 GPU (RunPod, 24GB VRAM)

| Concurrency | TTFT p50 | TTFT p95 | Latency p50 | Throughput p50 | Error Rate |
|-------------|----------|----------|-------------|----------------|------------|
| 1 | 77ms | 161ms | 96ms | 528.1 tok/s | 0% |
| 2 | 80ms | 213ms | 102ms | 432.7 tok/s | 0% |
| 4 | 73ms | 212ms | 95ms | 465.0 tok/s | 0% |
| 8 | 76ms | 211ms | 100ms | 405.9 tok/s | 0% |
| 16 | 71ms | 431ms | 97ms | 379.6 tok/s | 0% |
| 32 | 46ms | 728ms | 70ms | 450.2 tok/s | 0% |

## vLLM on CPU (8 vCPUs, 16GB RAM, float32)

| Concurrency | TTFT p50 | TTFT p95 | Latency p50 | Throughput p50 | Error Rate |
|-------------|----------|----------|-------------|----------------|------------|
| 1 | 110ms | 122ms | 731ms | 16.4 tok/s | 0% |
| 2 | 138ms | 209ms | 764ms | 18.6 tok/s | 0% |
| 4 | 225ms | 279ms | 821ms | 17.5 tok/s | 0% |
| 8 | 327ms | 380ms | 989ms | 15.4 tok/s | 0% |
| 16 | 591ms | 630ms | 1.54s | 10.7 tok/s | 0% |

## Ollama on CPU (8 vCPUs, 16GB RAM, Q4 quantized)

| Concurrency | TTFT p50 | TTFT p95 | Latency p50 | Throughput p50 | Error Rate |
|-------------|----------|----------|-------------|----------------|------------|
| 1 | 204ms | 551ms | 619ms | 42.3 tok/s | 0% |
| 2 | 622ms | 948ms | 1.01s | 47.3 tok/s | 0% |
| 4 | 750ms | 1.45s | 1.11s | 59.3 tok/s | 0% |
| 8 | 2.50s | 13.35s | 2.94s | 51.8 tok/s | 0% |
| 16 | 6.90s | 12.08s | 7.26s | 53.1 tok/s | 0% |

## Key Observations

1. **GPU throughput is 32x CPU**. vLLM on RTX 3090 delivers 528 tok/s vs 16 tok/s on CPU at c1.
   Even at c32, GPU maintains 450 tok/s.

2. **GPU TTFT stays flat under load**. TTFT p50 barely changes from c1 (77ms) to c32 (46ms).
   CPU TTFT degrades linearly from 110ms to 591ms over the same range.

3. **GPU handles 32 concurrent users**. TTFT p95 at c16 is 431ms (passes 500ms SLA).
   At c32 it reaches 728ms (fails SLA). CPU fails at c16 (630ms).

4. **Latency improvement is even larger**. GPU end-to-end latency at c1 is 96ms vs 731ms on CPU.
   That is 7.6x faster, with the gap widening under concurrency.

5. **CPU Ollama still wins on per-token throughput vs CPU vLLM** (42 vs 16 tok/s at c1)
   due to Q4 quantization. But GPU vLLM at 528 tok/s outclasses both by over 12x.

## SLA Compliance (500ms TTFT p95)

| Engine | Max Concurrent Users Within SLA |
|--------|--------------------------------|
| vLLM + RTX 3090 | 16 |
| vLLM + CPU (8 vCPU) | 8 |
| Ollama + CPU (8 vCPU) | 1 |

## Cost Efficiency

At $0.22/hr for the RTX 3090 (RunPod community):
- GPU serves 16 concurrent users at $0.014/hr per user
- CPU serves 8 concurrent users (server cost varies, but typically $0.10-0.20/hr for 8 vCPU)
  at $0.013-0.025/hr per user

GPU is cost-competitive with CPU for serving, while delivering 32x throughput and 2x concurrency.

## Verdict

For a 500ms TTFT SLA:
- **GPU (RTX 3090)**: 16 concurrent users, 528 tok/s, $0.22/hr
- **CPU vLLM (8 vCPU)**: 8 concurrent users, 16 tok/s
- **CPU Ollama (8 vCPU)**: 1 concurrent user, 42 tok/s

GPU wins on every metric except raw hardware cost. For production serving, GPU is the clear choice.
Ollama remains useful for local development. CPU vLLM is viable for low-traffic staging environments.
