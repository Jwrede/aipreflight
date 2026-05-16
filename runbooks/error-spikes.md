# Runbook: Error Spikes

## Symptom

Gate reports FAIL due to error rate exceeding threshold. Probes return status "error" with connection refused, timeout, or HTTP 5xx.

## Diagnosis steps

1. Check error types in the diagnosis output:

```bash
python3 scripts/diagnose.py runs/latest/llmprobe.jsonl
```

Look for the "Possible Causes" section which categorizes errors by type.

2. Check if errors correlate with load:

```bash
./scripts/sweep.sh configs/llmprobe/vllm.yml 1,2,4,8,16
```

If errors appear only at high concurrency: server is rejecting under load.
If errors appear at c1: server is unhealthy regardless of load.

## Common causes

| Error | Cause | Fix |
|-------|-------|-----|
| connection refused | Server not running or port mismatch | Verify server is up, check port binding |
| timeout | Server too slow to respond | Increase client timeout or reduce model load |
| HTTP 503 | Server overloaded, rejecting requests | Reduce concurrency, add replicas |
| HTTP 500 | Internal server error | Check server logs for OOM, CUDA errors |
| empty response | Model loaded but failing to generate | Check model config, max_tokens setting |

## Resolution

For connection errors:
- Verify the endpoint is reachable: `curl http://localhost:8000/health`
- Check if the model is still loading: `docker logs <container>`
- Verify port mapping matches the probe config

For timeout errors:
- Increase probe timeout in llmprobe config
- Check if max_model_len is causing extremely long generations
- Monitor memory usage for OOM conditions

For HTTP 5xx under load:
- Reduce `--max-num-seqs` to reject fewer requests
- Add request queue with bounded depth
- Scale horizontally behind a load balancer
- Check GPU memory for fragmentation issues

For intermittent errors:
- Check for container restarts: `docker ps --format "{{.Status}}"`
- Monitor system memory for OOM killer activity: `dmesg | grep -i oom`
- Check if Kubernetes is evicting or restarting pods
