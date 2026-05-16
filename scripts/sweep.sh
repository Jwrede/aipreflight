#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: sweep.sh [CONFIG] [LEVELS] [COUNT] [INTERVAL]"
    echo ""
    echo "Run llmprobe at increasing concurrency levels to find the SLA breaking point."
    echo ""
    echo "Defaults:"
    echo "  CONFIG    configs/llmprobe/vllm.yml"
    echo "  LEVELS    1,2,4,8      (comma-separated concurrency levels)"
    echo "  COUNT     10           (probes per instance per level)"
    echo "  INTERVAL  5s           (time between probes)"
    exit 0
}
[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

CONFIG="${1:-configs/llmprobe/vllm.yml}"
LEVELS="${2:-1,2,4,8}"
COUNT="${3:-10}"
INTERVAL="${4:-5s}"
SWEEP_DIR="runs/sweep-$(date +%Y%m%dT%H%M%S)"

mkdir -p "$SWEEP_DIR"

echo "Concurrency sweep"
echo "  Config:   $CONFIG"
echo "  Levels:   $LEVELS"
echo "  Count:    $COUNT probes per instance"
echo "  Interval: $INTERVAL"
echo "  Output:   $SWEEP_DIR"
echo ""

IFS=',' read -ra CONCURRENCY_LEVELS <<< "$LEVELS"

for level in "${CONCURRENCY_LEVELS[@]}"; do
    printf "  c%-3s " "$level"
    OUTDIR="$SWEEP_DIR/c${level}"
    mkdir -p "$OUTDIR"

    for _i in $(seq 1 "$level"); do
        llmprobe watch \
            --interval "$INTERVAL" \
            --count "$COUNT" \
            -f json \
            -c "$CONFIG" \
            >> "$OUTDIR/llmprobe.jsonl" 2>/dev/null &
    done
    wait

    PROBES=$(wc -l < "$OUTDIR/llmprobe.jsonl")
    python3 scripts/report.py "$OUTDIR/llmprobe.jsonl" > "$OUTDIR/readiness-report.md"
    printf "%3d probes collected\n" "$PROBES"
done

ln -sfn "$(basename "$SWEEP_DIR")" runs/latest

echo ""
python3 scripts/compare.py "$SWEEP_DIR" | tee "$SWEEP_DIR/comparison.md"
echo ""
echo "Full results: $SWEEP_DIR/comparison.md"
