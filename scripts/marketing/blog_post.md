# Your vLLM server says "healthy" while users wait 3 seconds for the first token

I ran a concurrency sweep on Qwen2 0.5B across three setups: vLLM on an RTX 3090, vLLM on CPU, and Ollama on CPU. The question was simple: how many concurrent users can each setup handle within a 500ms time-to-first-token SLA?

The answer surprised me.

## The data

| Concurrency | GPU TTFT p50 | GPU tok/s | CPU TTFT p50 | CPU tok/s | Ollama TTFT p50 | Ollama tok/s |
|-------------|--------------|-----------|--------------|-----------|-----------------|--------------|
| 1 | 77ms | 528 | 110ms | 16.4 | 204ms | 42.3 |
| 4 | 73ms | 465 | 225ms | 17.5 | 750ms | 59.3 |
| 8 | 76ms | 406 | 327ms | 15.4 | 2.50s | 51.8 |
| 16 | 71ms | 380 | 591ms | 10.7 | 6.90s | 53.1 |
| 32 | 46ms | 450 | N/A | N/A | N/A | N/A |

GPU (RTX 3090, $0.22/hr on RunPod). CPU (8 vCPUs, 16GB RAM). Model: Qwen2 0.5B on all three.

## What this means

For a 500ms TTFT SLA:

- **RTX 3090**: 16 concurrent users
- **CPU vLLM**: 8 concurrent users
- **CPU Ollama**: 1 concurrent user

Ollama has 3x the raw throughput of CPU vLLM (42 vs 16 tok/s) because of Q4 quantization. But its TTFT collapses under load. At c8, users wait 2.5 seconds for the first token. vLLM's continuous batching keeps TTFT flat.

The GPU delivers 32x throughput and TTFT that barely moves from c1 to c32. At $0.22/hr, that is $0.014 per concurrent user per hour.

## The real problem this exposed

I set up Prometheus to scrape vLLM's /metrics endpoint and compared server-reported TTFT with what the client actually measured.

At c16 under sustained load:
- Client TTFT p95: 941ms
- Server TTFT p95: 942ms
- Gap: 29ms

The gap was tiny. Good. That means the bottleneck was compute, not network. But if I had a misconfigured load balancer or a TLS proxy adding latency, server metrics would still say everything was fine. Only the client-side measurement would catch it.

This is the same reason you run Playwright tests even though your app has internal health checks. The server says "I'm fine" but the user sees something different. For LLM inference, the gap between what the server reports and what the user experiences is where incidents hide.

## The workflow I built

I wanted a tool that answers "can I route traffic to this endpoint right now?" with a binary yes/no. Not a dashboard. Not a graph. A verdict.

```
llmprobe (external)   ->  IS there a problem?     (client-side truth)
Prometheus (internal)  ->  WHY is there a problem?  (server-side explanation)
aipreflight            ->  WHAT to do about it      (automated verdict)
```

One command, `aipreflight check`, drives three workflows:

1. **Gate**: Run acceptance probes, check against an SLA contract, exit 0 or 1. Plugs into any CI/CD pipeline with no human in the loop.

2. **Diagnose**: Correlate client TTFT with server TTFT. If the gap is large, the problem is in the network layer. If both agree, check queue depth and KV cache. It tells you where to look.

3. **Capacity**: Ramp concurrency from 1 to 32. Find the exact point where your SLA breaks. "This config supports 16 concurrent users within 500ms TTFT."

The client-side probes come from [llmprobe](https://github.com/Jwrede/llmprobe), a Go tool I built for black-box LLM endpoint testing. It measures TTFT, latency, throughput, and error rates from outside the server.

## Beyond inference: the same gate for apps that just call an API

Most teams do not host their own model. They call a provider and ship prompt changes, RAG changes, and provider swaps with none of the preflight discipline that normal software takes for granted. The TTFT problem is real, but it is one instance of a bigger gap.

So aipreflight runs the same verdict machinery against two more kinds of target, with no GPU and no probe:

- An **app** profile prices the LLM call sites in your source with [tokentoll](https://github.com/Jwrede/tokentoll) and fails if the monthly bill exceeds budget, then checks that an eval suite, debuggable telemetry, and a rollback runbook are all in place.
- A **rag** profile runs your existing eval suite and gates on retrieval precision, citation rate, and hallucination rate.

The point of the RAG gate is the same as the TTFT point. A RAG system can be "up" while retrieval has silently regressed and the model has started answering unanswerable questions. The example app in the repo reproduces exactly that: flip one environment variable and readiness FAILs on a retrieval regression while the service itself never goes down. Infrastructure checks miss it. A preflight gate catches it.

## Limitations

- Prometheus correlation only works with vLLM (it is the only engine that exposes histogram metrics for TTFT and latency).
- The TTFT gap analysis assumes the client and server clocks are reasonably synchronized.
- Sweep results depend heavily on prompt length. These benchmarks use a fixed 20-token prompt. Real workloads with variable prompt lengths will show different curves.
- No GPU memory pressure testing yet. Qwen2 0.5B barely touches a 24GB card. Larger models would show KV cache effects.

## Try it

```bash
git clone https://github.com/Jwrede/aipreflight && cd aipreflight
pip install -e .

# No endpoint and no GPU needed for these two:
aipreflight check --profile profiles/app.yml
AIPREFLIGHT_RAG_BROKEN=1 aipreflight check --profile profiles/rag.yml

# Point the inference profile at your own vLLM/Ollama/OpenAI-compatible endpoint:
go install github.com/Jwrede/llmprobe@latest
aipreflight check --profile profiles/inference.yml
```

GitHub: https://github.com/Jwrede/aipreflight
