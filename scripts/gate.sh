#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: gate.sh [CONFIG] [THRESHOLDS] [DURATION] [INTERVAL] [OUTDIR]"
    echo ""
    echo "Run llmprobe acceptance probes and produce a pass/fail verdict."
    echo "Exit code 0 = pass (safe to route traffic), 1 = fail."
    echo ""
    echo "Defaults:"
    echo "  CONFIG      configs/llmprobe/vllm.yml"
    echo "  THRESHOLDS  thresholds.yml"
    echo "  DURATION    30s"
    echo "  INTERVAL    5s"
    exit 0
}
[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

CONFIG="${1:-configs/llmprobe/vllm.yml}"
THRESHOLDS="${2:-thresholds.yml}"
DURATION="${3:-30s}"
INTERVAL="${4:-5s}"
OUTDIR="${5:-runs/gate-$(date +%Y%m%dT%H%M%S)}"

mkdir -p "$OUTDIR"

echo "Running readiness gate..."
echo "  Config:     $CONFIG"
echo "  Thresholds: $THRESHOLDS"
echo "  Duration:   $DURATION"
echo "  Interval:   $INTERVAL"
echo ""

llmprobe watch \
    --interval "$INTERVAL" \
    --duration "$DURATION" \
    -f json \
    -c "$CONFIG" \
    > "$OUTDIR/llmprobe.jsonl" 2>/dev/null

ln -sfn "$(basename "$OUTDIR")" runs/latest

PROBES=$(wc -l < "$OUTDIR/llmprobe.jsonl")
echo "Collected $PROBES probes."
echo ""

python3 scripts/report.py --gate --thresholds "$THRESHOLDS" "$OUTDIR/llmprobe.jsonl" \
    | tee "$OUTDIR/gate-result.txt"
EXIT_CODE=${PIPESTATUS[0]}

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "GATE: PASS"
else
    echo "GATE: FAIL"
    echo "Diagnose: python3 scripts/diagnose.py $OUTDIR/llmprobe.jsonl --prometheus http://localhost:9090"
fi

exit $EXIT_CODE
