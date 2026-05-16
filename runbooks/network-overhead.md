# Runbook: Network/Proxy Overhead

## Symptom

Client TTFT p95 exceeds server TTFT p95 by more than 100ms. Diagnose.py reports "Network/proxy overhead detected."

## Diagnosis steps

1. Run diagnosis with Prometheus to confirm the gap:

```bash
python3 scripts/diagnose.py runs/latest/llmprobe.jsonl --prometheus http://localhost:9090
```

Look for: "Client TTFT p95 (Xms) exceeds server TTFT p95 (Yms) by Zms."

2. Identify the source of the gap:

The gap represents time spent outside the inference engine. Possible locations:
- DNS resolution
- TCP connection setup
- TLS handshake
- Load balancer queuing
- Reverse proxy processing
- Network latency (physical distance)

## Common causes

| Cause | Evidence | Fix |
|-------|----------|-----|
| TLS termination | Gap appears only with HTTPS | Use connection pooling or move TLS closer |
| Load balancer | Gap appears with any backend | Check LB health check config and routing |
| DNS resolution | Gap varies across probes | Use connection reuse or cache DNS |
| Geographic distance | Consistent gap ~50-150ms | Deploy probe client closer to endpoint |
| Proxy buffering | Gap grows with response size | Disable proxy buffering for streaming |

## Resolution

- Bypass unnecessary proxy layers for internal health checks
- Use HTTP/2 or keep-alive connections to amortize handshake cost
- Move the probe client to the same network as the inference server
- Check if the load balancer adds X-Request-Start or similar timing headers
- For streaming endpoints, ensure proxies pass through chunks immediately
- If using Kubernetes, check service mesh sidecar overhead (Istio, Linkerd)
