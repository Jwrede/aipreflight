# RunPod GPU Setup (Reproducibility Guide)

How to reproduce the GPU benchmarks from this project on RunPod.

## Prerequisites

- RunPod account with GPU credits
- Python 3.10+ with `runpod` package (`pip install runpod`)
- `RUNPOD_API_KEY` environment variable set
- llmprobe installed (`go install github.com/Jwrede/llmprobe@latest`)

## 1. Launch a GPU Pod

```python
import runpod

pod = runpod.create_pod(
    name="vllm-benchmark",
    image_name="vllm/vllm-openai:latest",
    gpu_type_id="NVIDIA GeForce RTX 3090",
    gpu_count=1,
    volume_in_gb=0,
    ports="8000/http",
    docker_args="--model Qwen/Qwen2-0.5B-Instruct --max-model-len 2048 --gpu-memory-utilization 0.9",
)
print(f"Pod ID: {pod['id']}")
```

Alternative GPUs (tested):
- `NVIDIA GeForce RTX 3090` ($0.22/hr community, $0.44/hr secure)
- `NVIDIA RTX A4000` ($0.26/hr)
- `NVIDIA A100 80GB` ($1.64/hr)

## 2. Wait for Model Loading

vLLM takes 30-60s to download and load the model. Poll the health endpoint:

```bash
POD_ID="your-pod-id"
BASE_URL="https://${POD_ID}-8000.proxy.runpod.net"

until curl -sf "${BASE_URL}/health" > /dev/null 2>&1; do
  echo "Waiting for vLLM..."
  sleep 10
done
echo "Ready"
```

## 3. Configure llmprobe

Create or edit `configs/llmprobe/runpod-gpu.yml`:

```yaml
providers:
  - name: openai
    label: runpod-gpu
    api_key: unused
    base_url: https://<pod-id>-8000.proxy.runpod.net
    models:
      - name: Qwen/Qwen2-0.5B-Instruct
        thresholds:
          max_ttft: 3s
          max_latency: 30s
          min_throughput: 2
```

Replace `<pod-id>` with your actual pod ID.

## 4. Run Benchmarks

```bash
# Readiness gate
./scripts/gate.sh configs/llmprobe/runpod-gpu.yml thresholds.yml 30s 5s

# Concurrency sweep (find breaking point)
./scripts/sweep.sh configs/llmprobe/runpod-gpu.yml 1,2,4,8,16,32
```

## 5. Terminate the Pod

```python
import runpod
runpod.terminate_pod(pod["id"])
```

Or via CLI: `runpodctl remove pod <pod-id>`

## Cost

Full benchmark suite (gate + sweep at 6 concurrency levels) takes approximately 5-8 minutes.
At $0.22/hr for an RTX 3090, total cost is under $0.03.

## Expected Results (RTX 3090, Qwen2 0.5B)

| Concurrency | TTFT p50 | Throughput p50 |
|-------------|----------|----------------|
| 1 | 77ms | 528 tok/s |
| 4 | 73ms | 465 tok/s |
| 8 | 76ms | 406 tok/s |
| 16 | 71ms | 380 tok/s |
| 32 | 46ms | 450 tok/s |

TTFT stays flat under load due to continuous batching. Throughput drops ~28% from c1 to c16
as compute is shared across requests, then recovers at c32 as batch efficiency improves.

## Troubleshooting

**Pod starts but /health returns 503**: Model still loading. Wait 60s. Check logs:
`runpodctl logs <pod-id>`

**Connection refused**: RunPod proxy takes 10-20s after pod is ready. Retry.

**TTFT much higher than expected**: Check if RunPod assigned you a different GPU than requested
(community cloud). Verify with `curl ${BASE_URL}/v1/models`.

**OOM with larger models**: Reduce `--gpu-memory-utilization` to 0.85 or use a GPU with more VRAM.
