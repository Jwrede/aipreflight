# inference-readiness-kit

Operator workflow that answers: **Is this LLM inference endpoint ready to serve traffic, and what breaks first?**

Combines black-box endpoint measurements from [llmprobe](https://github.com/Jwrede/llmprobe) with server-side inference metrics (vLLM, SGLang) to produce structured readiness reports.

## How it works

```
llmprobe watch ──> llmprobe.jsonl ──> generate_report.py ──> readiness-report.md
                                              ↑
                          prometheus-metrics.json (optional, Phase 2)
```

1. `run_probe.sh` drives llmprobe to collect black-box measurements (TTFT, latency, throughput, errors).
2. `generate_report.py` analyzes the JSONL and produces a Markdown readiness report with a pass/fail judgment.
3. (Phase 2) Prometheus queries pull server-side metrics (queue depth, KV cache, running requests) and the report correlates them with black-box observations.

## Output structure

Each run produces a timestamped directory:

```
runs/20260516T100000/
  llmprobe.jsonl          # Raw probe data
  llmprobe-report.md      # llmprobe's built-in percentile report
  readiness-report.md     # This project's readiness judgment
```

## Quick start

Prerequisites: [llmprobe](https://github.com/Jwrede/llmprobe) installed, Python 3.10+.

```bash
# Edit the config to point at your endpoint
vim configs/llmprobe/vllm.yml

# Run a 60-second probe session
./scripts/run_probe.sh configs/llmprobe/vllm.yml 60s 10s

# Or generate a report from existing JSONL
python3 scripts/generate_report.py runs/20260516T100000/llmprobe.jsonl
```

## Example report

See [reports/examples/sample-readiness-report.md](reports/examples/sample-readiness-report.md) for output from a simulated vLLM session with intermittent degradation.

## How this differs from llmprobe

| | llmprobe | inference-readiness-kit |
|---|---|---|
| Scope | Black-box endpoint probing | Joined black-box + server-side diagnosis |
| Output | JSONL, percentile tables | Readiness judgment with actionable next steps |
| Server metrics | No | vLLM/SGLang Prometheus queries |
| Judgment | Per-probe pass/fail | Aggregate readiness decision |

## Roadmap

- [x] P0: Probe runner, report generator, example output
- [ ] P1: Concurrency sweep scripts
- [ ] P2: Prometheus collector for vLLM server metrics
- [ ] P3: Real vLLM CPU experiment with published results

## License

MIT
