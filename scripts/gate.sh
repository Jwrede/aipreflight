#!/usr/bin/env bash
set -euo pipefail

CONFIG="${1:-configs/llmprobe/vllm.yml}"
THRESHOLDS="${2:-thresholds.yml}"
DURATION="${3:-30s}"
INTERVAL="${4:-5s}"
OUTDIR="${5:-runs/gate-$(date +%Y%m%dT%H%M%S)}"

mkdir -p "$OUTDIR"

echo "Running readiness gate..."
echo "  Config: $CONFIG"
echo "  Thresholds: $THRESHOLDS"
echo "  Duration: $DURATION"
echo ""

llmprobe watch \
    --interval "$INTERVAL" \
    --duration "$DURATION" \
    -f json \
    -c "$CONFIG" \
    > "$OUTDIR/llmprobe.jsonl"

python3 scripts/report.py --gate --thresholds "$THRESHOLDS" "$OUTDIR/llmprobe.jsonl" \
    | tee "$OUTDIR/gate-result.txt"
EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "GATE: PASS -- safe to route traffic"
else
    echo ""
    echo "GATE: FAIL -- do not route traffic"
    echo "Run: python3 scripts/diagnose.py $OUTDIR/llmprobe.jsonl"
fi

exit $EXIT_CODE
