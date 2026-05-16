#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/llmprobe/vllm.yml}"
DURATION="${2:-60s}"
INTERVAL="${3:-10s}"
OUTDIR="${4:-runs/$(date +%Y%m%dT%H%M%S)}"

mkdir -p "$OUTDIR"

echo "Probing for $DURATION at $INTERVAL intervals..."
echo "Config: $CONFIG"
echo "Output: $OUTDIR"

llmprobe watch \
  --interval "$INTERVAL" \
  --duration "$DURATION" \
  -f json \
  -c "$CONFIG" \
  > "$OUTDIR/llmprobe.jsonl"

echo "Generating report..."
llmprobe report "$OUTDIR/llmprobe.jsonl" > "$OUTDIR/llmprobe-report.md"

echo "Generating readiness report..."
python3 scripts/generate_report.py "$OUTDIR/llmprobe.jsonl" > "$OUTDIR/readiness-report.md"

echo "Done. Results in $OUTDIR/"
