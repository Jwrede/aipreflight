#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/llmprobe/vllm.yml}"
LEVELS="${2:-1,2,4,8}"
DURATION="${3:-60s}"
INTERVAL="${4:-5s}"
SWEEP_DIR="runs/sweep-$(date +%Y%m%dT%H%M%S)"

mkdir -p "$SWEEP_DIR"

echo "Concurrency sweep: levels=$LEVELS, duration=$DURATION, interval=$INTERVAL"
echo "Output: $SWEEP_DIR"
echo ""

IFS=',' read -ra CONCURRENCY_LEVELS <<< "$LEVELS"

for level in "${CONCURRENCY_LEVELS[@]}"; do
    echo "=== Concurrency $level ==="
    OUTDIR="$SWEEP_DIR/c${level}"
    mkdir -p "$OUTDIR"

    llmprobe watch \
        --interval "$INTERVAL" \
        --duration "$DURATION" \
        --concurrency "$level" \
        -f json \
        -c "$CONFIG" \
        > "$OUTDIR/llmprobe.jsonl"

    python3 scripts/generate_report.py "$OUTDIR/llmprobe.jsonl" > "$OUTDIR/readiness-report.md"
    echo "  Done. $(wc -l < "$OUTDIR/llmprobe.jsonl") probes collected."
    echo ""
done

echo "Generating comparison..."
python3 scripts/compare_sweep.py "$SWEEP_DIR" > "$SWEEP_DIR/comparison.md"
echo "Sweep complete. See $SWEEP_DIR/comparison.md"
