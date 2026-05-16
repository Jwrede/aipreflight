# Runbook: KV Cache Pressure

## Symptom

Prometheus shows `vllm:kv_cache_usage_perc` > 80%. Diagnose.py reports "KV cache pressure" in correlation analysis.

## Diagnosis steps

1. Check KV cache usage during load:

```bash
python3 scripts/diagnose.py runs/latest/llmprobe.jsonl --prometheus http://localhost:9090
```

Look for: "KV cache pressure: Peak usage N%."

2. Correlate with TTFT spikes:

When KV cache is full, vLLM preempts (evicts) sequences and recomputes them later. This causes TTFT spikes for the evicted requests.

Check `vllm:num_preemptions_total` in Prometheus for confirmation.

## Common causes

| Cause | Evidence | Fix |
|-------|----------|-----|
| Long sequences | Cache fills with few requests | Reduce max_model_len |
| High concurrency | Many short requests fill cache | Reduce max_num_seqs |
| Large model context | Model uses most of available memory | Increase GPU memory or use quantization |
| No prefix caching | Repeated prefixes stored separately | Enable prefix caching |

## Resolution

- Reduce `--max-model-len` to limit per-request KV allocation
- Enable `--enable-prefix-caching` for shared system prompts
- Reduce `--max-num-seqs` to limit concurrent cache consumers
- Use quantized KV cache (`--kv-cache-dtype fp8_e5m2`) to halve cache memory
- Add GPU memory or use tensor parallelism across GPUs
- Monitor `vllm:num_preemptions_total` to confirm preemption is happening
