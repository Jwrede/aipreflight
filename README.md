![aipreflight](docs/thumbnail.png)

# aipreflight

SRE-style preflight checks for AI applications. One command, one readiness report, one ship/block verdict.

aipreflight brings the deployment discipline of CI gates, smoke tests, and SLO-based rollouts to LLM apps, RAG systems, and inference endpoints. It turns external acceptance testing ([llmprobe](https://github.com/Jwrede/llmprobe)) and internal server telemetry (Prometheus) into an automated go/no-go decision before traffic is routed.

> Formerly `inference-readiness-kit`. The project keeps its strongest proof, SLA gating for self-hosted inference, and has broadened into a general production readiness gate for AI applications. It now ships three profiles: `inference` (SLA gating), `app` (cost, evals, observability, rollback for hosted-API apps), and `rag` (retrieval and answer quality). See [TODO.md](TODO.md) for the implementation plan.

![demo](demo/demo.gif)

## The problem

Server metrics say "healthy" while users experience 3-second TTFT. The load balancer is misconfigured, TLS adds overhead, the rate limiter is throttling, or the model is silently returning empty responses. Server-side metrics alone often miss this because they do not measure the full client path. You need an external validator.

## When to use this

Run `aipreflight check` at the same gates where classical software already runs CI checks, smoke tests, and canary analysis:

- Before merging an AI feature, prompt change, or RAG change.
- Before routing traffic to a new model or a new provider.
- Before increasing a rollout percentage.
- Before approving a customer pilot or a production launch.

Each gate gives you one verdict and one exit code, so it drops into a pull request check, a deploy step, or a Kubernetes Job without a human in the loop.

## How it works

```
llmprobe (external)   -->  IS there a problem?     (client-side truth)
Prometheus (internal) -->  WHY is there a problem?  (server-side explanation)
aipreflight           -->  WHAT to do about it      (automated verdict)
```

See [docs/architecture.md](docs/architecture.md) for the full flow: how a profile,
the external signals, and the per-check verdict aggregation produce one report and
one exit code.

## Three workflows

### 1. Gate (CI/CD)

Deploy a new model, run acceptance probes, get a readiness verdict. Exit code 0 = pass, 1 = fail, 2 = config error, 3 = probe error.

```bash
aipreflight check --profile profiles/inference.yml
# Verdict: PASS  (safe to route traffic)
# Verdict: FAIL  (do not route traffic)
```

Writes `runs/latest/aipreflight-report.json` and `.md` with the verdict, failed checks, and metrics. Integrates into any CI/CD pipeline with no human in the loop. The legacy `./scripts/gate.sh` is still supported and now wraps this command.

### 2. Diagnose (incident response)

Users report slow responses. Correlate client observations with server state.

```bash
aipreflight diagnose runs/latest --prometheus http://localhost:9090
```

Output tells you whether the problem is in the network layer (client/server TTFT gap), the inference engine (queue depth, KV cache pressure), or upstream (errors, timeouts).

### 3. Capacity (planning)

Find the concurrency level where your endpoint breaks its SLA.

```bash
./scripts/sweep.sh configs/llmprobe/vllm.yml 1,2,4,8,16
```

Produces a comparison table showing how TTFT, latency, and throughput degrade under load. Tells you exactly how many concurrent users your config supports within SLA.

## Profiles: inference, app, and rag

A profile defines what "ready" means for one kind of target. `aipreflight check`
runs the right checks and aggregates them into one verdict (PASS / WARN / FAIL).

| Profile | Kind | Needs | Checks |
|---------|------|-------|--------|
| `profiles/inference.yml` | `inference` | llmprobe (+ optional Prometheus) | TTFT, latency, throughput, error rate vs SLA |
| `profiles/app.yml` | `app` | nothing self-hosted | cost budget (tokentoll), eval quality gate, observability fields, rollback runbook |
| `profiles/rag.yml` | `rag` | nothing self-hosted | retrieval precision, answer quality, citation rate, hallucination rate, empty-retrieval handling, observability, rollback |

The `app` profile is for teams calling hosted APIs that still need production
discipline: a cost gate, a quality eval suite, debuggable telemetry, and a
rollback path. It runs with no GPU and no probe. See
[examples/hosted-api-app](examples/hosted-api-app) for a runnable target.

The `rag` profile gates the quality signals that infrastructure checks miss: a
RAG system can be "up" while retrieval has regressed, answers have stopped citing
sources, or the model has begun answering unanswerable questions. See
[examples/rag-app](examples/rag-app) for a runnable offline target that fails
readiness on a retrieval regression while the service itself stays healthy.

## Quality gate

`app` and `rag` profiles can gate on the results of an eval suite, not just check
that one is configured. aipreflight does not implement evals. It runs whatever
eval command you already have (pytest, promptfoo, ragas, a custom script), reads
its JSON output, and turns it into one pass/fail gate:

```yaml
evals:
  command: "python evals/run_evals.py"   # emits JSON on stdout
  results_file: evals/results.json       # optional: read this instead of stdout
  min_pass_rate: 0.9                      # gate on overall pass rate
  metrics:                                # optional per-metric gates
    retrieval_precision: {min: 0.8}
    hallucination_rate: {max: 0.05}
```

The eval step must emit JSON with `total`/`passed` (or `pass_rate`) and an
optional `metrics` map. The eval command's own exit code does not decide the
gate; the reported numbers do. Without `min_pass_rate`/`metrics`, the check falls
back to verifying an eval suite is configured and present (run it in CI).

```bash
aipreflight check --profile profiles/app.yml
# Verdict: PASS
# cost          PASS   $7.69/mo across 1 call site(s), within budget
# evals         PASS   eval suite configured
# observability PASS   telemetry config present with all 9 required fields
# deployment    PASS   rollback runbook present
```

The cost gate uses [tokentoll](https://github.com/Jwrede/tokentoll) to statically
price the LLM call sites in your source and fail if per-request or monthly cost
exceeds the budget in the profile.

## Quick start

Prerequisites: [llmprobe](https://github.com/Jwrede/llmprobe) v1.4.0+, Python 3.10+. The app profile additionally uses [tokentoll](https://github.com/Jwrede/tokentoll) (`pip install tokentoll`).

```bash
go install github.com/Jwrede/llmprobe@latest
git clone https://github.com/Jwrede/aipreflight && cd aipreflight
pip install -e .

# Point the inference profile at your endpoint (vLLM, Ollama, or any OpenAI-compatible server)
vim configs/llmprobe/vllm.yml   # referenced by profiles/inference.yml

# Run the readiness gate (exit 0 = pass, 1 = fail, 2 = config error, 3 = probe error)
aipreflight check --profile profiles/inference.yml

# Score an existing probe run offline (no endpoint or GPU needed)
aipreflight check --profile profiles/inference.yml --probes fixtures/sample-probes.jsonl

# Check a hosted-API app instead (no llmprobe or GPU): cost, evals, observability, rollback
aipreflight check --profile profiles/app.yml

# Check a RAG app (no llmprobe or GPU): retrieval, answer quality, citations, hallucination
aipreflight check --profile profiles/rag.yml

# Find the concurrency breaking point
./scripts/sweep.sh configs/llmprobe/vllm.yml 1,2,4,8,16

# Diagnose with server-side metrics (requires Prometheus scraping your endpoint)
aipreflight diagnose runs/latest --prometheus http://localhost:9090
```

## Configuration

A **profile** bundles everything a check needs: how to probe, the SLA contract to gate on, and optional observability settings. `profiles/inference.yml` reproduces the original gate:

```yaml
name: inference
probe:
  config: configs/llmprobe/vllm.yml   # llmprobe config for your endpoint
  duration: 30s
  interval: 5s
thresholds:
  sla:
    ttft_ms: 500          # Max acceptable TTFT (p95)
    latency_ms: 10000     # Max acceptable end-to-end latency (p95)
    min_throughput: 3.0   # Min acceptable throughput (p50, tok/s)
    max_error_rate: 0.01  # Max acceptable error rate
  gate:
    min_probes: 5         # Minimum probes before making a decision
    pass_rate: 0.95       # Required healthy probe rate
observability:
  prometheus: null        # set to http://localhost:9090 to enable diagnose
  queries: configs/prometheus/queries.yml
```

Invalid profiles fail fast with exit code 2 and an actionable message. The standalone `thresholds.yml` is still read by the legacy `scripts/gate.sh` path. `configs/prometheus/queries.yml` defines which server metrics to collect for diagnosis.

## Running Prometheus with vLLM

vLLM exposes a `/metrics` endpoint by default. To correlate client probes with server telemetry:

```bash
# 1. Start vLLM (Docker CPU example)
docker run -d --name vllm -p 8000:8000 \
  vllm/vllm-openai-cpu:latest \
  --model Qwen/Qwen2-0.5B-Instruct --max-model-len 512

# 2. Start Prometheus
cp prometheus.example.yml prometheus.yml
# Edit prometheus.yml target if vLLM is not on host.docker.internal:8000
docker run -d --name prometheus -p 9090:9090 \
  --add-host=host.docker.internal:host-gateway \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
  prom/prometheus:latest

# 3. Verify scraping works
curl -s http://localhost:9090/api/v1/targets | grep '"health":"up"'

# 4. Run probes and diagnose
aipreflight check --profile profiles/inference.yml
aipreflight diagnose runs/latest --prometheus http://localhost:9090
```

The diagnosis correlates client-observed TTFT with server-reported TTFT. A large gap (>100ms) indicates network or proxy overhead between the client and the inference engine.

## Grafana Dashboard

A pre-built dashboard visualizes the same metrics used by `aipreflight diagnose`. Grafana is for inspection; the readiness gate remains the source of deployment decisions.

```bash
# 1. Make sure prometheus.yml exists
cp prometheus.example.yml prometheus.yml

# 2. Start Prometheus + Grafana (Grafana on port 3001)
docker compose -f docker-compose.observability.yml up -d

# 3. Open in browser
open http://localhost:3001/d/vllm-readiness
# Login: admin / admin (or anonymous access enabled by default)
```

![Grafana dashboard under concurrency ramp](docs/grafana-dashboard.png)

Panels: TTFT p95/p50, end-to-end latency, running/waiting requests, KV cache usage, GPU utilization, GPU memory, GPU temperature/power, queue wait time, token throughput. Color thresholds match the SLA defaults in `thresholds.yml`.

To stop:

```bash
docker compose -f docker-compose.observability.yml down
```

## Kubernetes Deployment

Deploy vLLM with GPU scheduling and use aipreflight as the readiness probe:

```bash
# Deploy vLLM with GPU and readiness probes
kubectl apply -f k8s/vllm-deployment.yml
kubectl apply -f k8s/vllm-service.yml

# Deploy DCGM exporter for GPU metrics (requires NVIDIA GPU Operator)
kubectl apply -f k8s/dcgm-exporter.yml
kubectl apply -f k8s/servicemonitor.yml

# Run readiness gate as a Job (post-deploy validation)
kubectl apply -f k8s/readiness-gate-job.yml
kubectl logs -f job/aipreflight-gate
```

The Deployment uses `nvidia.com/gpu` resource requests, a `/health` readiness probe for basic liveness, and the readiness gate Job for SLA validation after deployment. DCGM exporter feeds GPU utilization, memory, and temperature into Prometheus alongside vLLM inference metrics.

See [docs/runpod-gpu-setup.md](docs/runpod-gpu-setup.md) for reproducing GPU benchmarks on RunPod.

## Real experiment results

Concurrency sweep on Qwen2 0.5B across GPU and CPU:

| Concurrency | GPU TTFT p50 | GPU tok/s | CPU TTFT p50 | CPU tok/s | Ollama TTFT p50 | Ollama tok/s |
|-------------|--------------|-----------|--------------|-----------|-----------------|--------------|
| 1 | 77ms | 528 | 110ms | 16.4 | 204ms | 42.3 |
| 4 | 73ms | 465 | 225ms | 17.5 | 750ms | 59.3 |
| 8 | 76ms | 406 | 327ms | 15.4 | 2.50s | 51.8 |
| 16 | 71ms | 380 | 591ms | 10.7 | 6.90s | 53.1 |
| 32 | 46ms | 450 | N/A | N/A | N/A | N/A |

GPU (RTX 3090, $0.22/hr): 32x throughput, TTFT stays flat under load. For a 500ms TTFT SLA:

| Engine | Max Concurrent Users Within SLA |
|--------|--------------------------------|
| vLLM + RTX 3090 | 16 |
| vLLM + CPU (8 vCPU) | 8 |
| Ollama + CPU (8 vCPU) | 1 |

Full analysis: [reports/examples/cross-engine-comparison.md](reports/examples/cross-engine-comparison.md)

## Example outputs

- [GPU readiness report (RTX 3090, c16)](reports/examples/gpu-c16-readiness-report.md)
- [GPU concurrency sweep](reports/examples/gpu-concurrency-sweep.md)
- [Cross-engine comparison (GPU vs CPU vs Ollama)](reports/examples/cross-engine-comparison.md)
- [Prometheus diagnosis (c16 under load)](reports/examples/prometheus-diagnosis-c16.md)
- [CPU readiness report (SLA violation at c16)](reports/examples/vllm-cpu-c16-readiness-report.md)
- [CPU concurrency sweep](reports/examples/vllm-cpu-concurrency-sweep.md)

## Project structure

```
aipreflight/                      # Python package (CLI + readiness logic)
  cli.py                         # `aipreflight` entrypoint (check/report/diagnose)
  profile.py                     # profile loading + validation (inference | app | rag)
  checks.py                      # generic CheckResult + verdict aggregation
  probes.py                      # llmprobe runner + JSONL loading
  analyze.py                     # SLA gate logic (inference)
  appcheck.py                    # app readiness checks (cost/evals/observability/deploy)
  cost.py                        # tokentoll cost gate adapter
  evals.py                       # eval quality gate adapter (pass rate + metrics)
  report.py                      # unified JSON + Markdown report
  diagnose.py                    # client + server + GPU correlation
  compare.py                     # sweep comparison table
profiles/
  inference.yml                  # vLLM / OpenAI-compatible endpoint profile
  app.yml                        # hosted-API app profile (cost/evals/observability)
  rag.yml                        # RAG profile (retrieval/answer quality gate)
examples/
  hosted-api-app/                # runnable FastAPI app checked by profiles/app.yml
  rag-app/                       # runnable offline RAG app checked by profiles/rag.yml
thresholds.yml                    # legacy SLA contract (scripts/gate.sh)
prometheus.example.yml            # Prometheus config template
docker-compose.observability.yml  # Prometheus + Grafana + DCGM stack
k8s/
  vllm-deployment.yml            # vLLM with GPU scheduling + readiness probe
  vllm-service.yml               # ClusterIP service
  readiness-gate-job.yml         # Post-deploy SLA validation Job
  dcgm-exporter.yml              # NVIDIA DCGM GPU metrics DaemonSet
  servicemonitor.yml             # Prometheus ServiceMonitors
grafana/
  dashboard.json                 # vLLM + GPU metrics dashboard
  provisioning/                  # Auto-config for datasource + dashboard
configs/
  llmprobe/vllm.yml             # vLLM probe configuration
  llmprobe/vllm-k8s.yml         # In-cluster vLLM probe configuration
  llmprobe/ollama.yml           # Ollama probe configuration
  llmprobe/runpod-gpu.yml       # RunPod GPU probe template
  prometheus/queries.yml         # Server + GPU metric queries
scripts/
  gate.sh                       # CI/CD readiness gate (wraps `aipreflight check`)
  sweep.sh                      # Concurrency sweep
  diagnose.py                   # Wrapper -> `aipreflight diagnose`
  compare.py                    # Wrapper -> sweep comparison table
  report.py                     # Wrapper -> standalone readiness report
docs/
  runpod-gpu-setup.md           # GPU benchmark reproducibility guide
fixtures/                       # Test data
tests/                          # pytest suite
runbooks/                       # Failure mode runbooks + rollback.md (app deployment check)
reports/examples/               # Example outputs
.github/workflows/ci.yml       # CI (pytest + shellcheck)
```

## Roadmap

- [x] Readiness gate with SLA thresholds
- [x] Diagnosis framework (client-only and with Prometheus)
- [x] Concurrency sweep with comparison
- [x] Real vLLM CPU experiment with published results
- [x] Cross-engine comparison (vLLM vs Ollama)
- [x] Prometheus-based server-side correlation with live data
- [x] Runbooks for common failure modes
- [x] Kubernetes manifests with GPU scheduling
- [x] NVIDIA DCGM GPU metrics in Prometheus/Grafana
- [x] `aipreflight` CLI with profiles, exit-code contract, and unified JSON/MD report
- [x] App profile with tokentoll cost gate, observability, and rollback checks
- [x] Runnable hosted-API example app (FastAPI, offline-testable)
- [x] Eval/quality gate (run the eval suite and gate on pass rate + metrics)
- [x] RAG profile and offline example (retrieval + answer quality readiness)

## What this does not replace

aipreflight is a gate, not a platform. It runs the checks you point it at and turns them into one verdict. It does not replace the tools that produce the underlying signals:

- It does not replace your LLM router or proxy (LiteLLM).
- It does not replace your metrics stack (Prometheus, Grafana, OpenTelemetry). It reads from Prometheus during `diagnose`.
- It does not replace your eval framework (promptfoo, Ragas, pytest). It runs whatever eval command you already have and gates on its results.
- It does not replace your orchestrator (Kubernetes). It runs as a Job or a CI step inside it.

The gap it fills is the preflight verdict: deciding, in one command, whether quality, cost, latency, observability, and rollback readiness are good enough to ship.

## License

MIT
