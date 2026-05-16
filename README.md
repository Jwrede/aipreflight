# inference-readiness-kit

Automated go/no-go decisions for LLM inference deployments.

Like readiness probes for Kubernetes, but for LLM inference SLAs. Combines external acceptance testing ([llmprobe](https://github.com/Jwrede/llmprobe)) with internal server telemetry (Prometheus) to make deployment decisions.

## The problem

Server metrics say "healthy" while users experience 3-second TTFT. The load balancer is misconfigured, TLS adds overhead, the rate limiter is throttling, or the model is silently returning empty responses. Server-side metrics cannot detect any of this. You need an external validator.

## How it works

```
llmprobe (external)  ──>  IS there a problem?     (client-side truth)
Prometheus (internal) ──>  WHY is there a problem?  (server-side explanation)
readiness-kit         ──>  WHAT to do about it      (automated verdict)
```

## Three workflows

### 1. Gate (CI/CD)

Deploy a new model, run acceptance probes, get a binary pass/fail. Exit code 0 or 1.

```bash
./scripts/gate.sh configs/llmprobe/vllm.yml thresholds.yml 30s 5s
# GATE: PASS -- safe to route traffic
# GATE: FAIL -- do not route traffic
```

Integrates into any CI/CD pipeline. No human in the loop.

### 2. Diagnose (incident response)

Users report slow responses. Correlate client observations with server state.

```bash
python3 scripts/diagnose.py runs/latest/llmprobe.jsonl --prometheus http://localhost:9090
```

Output tells you whether the problem is in the network layer (client/server TTFT gap), the inference engine (queue depth, KV cache pressure), or upstream (errors, timeouts).

### 3. Capacity (planning)

Find the concurrency level where your endpoint breaks its SLA.

```bash
./scripts/sweep.sh configs/llmprobe/vllm.yml 1,2,4,8,16
```

Produces a comparison table showing how TTFT, latency, and throughput degrade under load. Tells you exactly how many concurrent users your config supports within SLA.

## Quick start

Prerequisites: [llmprobe](https://github.com/Jwrede/llmprobe) (`go install github.com/Jwrede/llmprobe@latest`), Python 3.10+, PyYAML.

```bash
pip install pyyaml

# Edit thresholds to match your SLA
vim thresholds.yml

# Edit the probe config to point at your endpoint
vim configs/llmprobe/vllm.yml

# Run the gate check
./scripts/gate.sh
```

## Configuration

**thresholds.yml** defines your SLA contract:

```yaml
sla:
  ttft_ms: 500          # Max acceptable TTFT (p95)
  latency_ms: 10000     # Max acceptable end-to-end latency (p95)
  min_throughput: 3.0   # Min acceptable throughput (p50, tok/s)
  max_error_rate: 0.01  # Max acceptable error rate

gate:
  min_probes: 5         # Minimum probes before making a decision
  pass_rate: 0.95       # Required healthy probe rate
```

**configs/prometheus/queries.yml** defines which server metrics to collect for diagnosis.

## Output example

See [reports/examples/sample-readiness-report.md](reports/examples/sample-readiness-report.md) for a full report from a simulated vLLM session with degradation.

## Project structure

```
thresholds.yml                    # SLA contract
configs/
  llmprobe/vllm.yml              # Probe configuration
  prometheus/queries.yml          # Server-side metric queries
scripts/
  gate.sh                        # CI/CD readiness gate (exit 0/1)
  diagnose.py                    # Client + server correlation
  sweep.sh                       # Concurrency sweep
  compare.py                     # Sweep comparison table
  report.py                      # Full readiness report with verdict
fixtures/                        # Test data
reports/examples/                # Example outputs
```

## Roadmap

- [x] Readiness gate with SLA thresholds
- [x] Diagnosis framework (client-only and with Prometheus)
- [x] Concurrency sweep with comparison
- [ ] Real vLLM CPU experiment with published results
- [ ] Runbooks for common failure modes

## License

MIT
