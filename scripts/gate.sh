#!/usr/bin/env bash
set -euo pipefail

# Thin wrapper around `aipreflight check`. Kept so existing pipelines and the
# k8s Job keep working. The SLA thresholds now live in profiles/inference.yml;
# the THRESHOLDS argument is accepted for backward compatibility but ignored.

usage() {
    echo "Usage: gate.sh [CONFIG] [THRESHOLDS] [DURATION] [INTERVAL] [OUTDIR]"
    echo ""
    echo "Run llmprobe acceptance probes and produce a pass/fail verdict."
    echo "Exit code 0 = pass, 1 = fail, 2 = config error, 3 = probe error."
    echo ""
    echo "Equivalent to:"
    echo "  aipreflight check --profile profiles/inference.yml \\"
    echo "    --config CONFIG --duration DURATION --interval INTERVAL --out OUTDIR"
    echo ""
    echo "Defaults:"
    echo "  CONFIG      configs/llmprobe/vllm.yml"
    echo "  THRESHOLDS  (ignored; defined in profiles/inference.yml)"
    echo "  DURATION    30s"
    echo "  INTERVAL    5s"
    exit 0
}
[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage

CONFIG="${1:-configs/llmprobe/vllm.yml}"
# shellcheck disable=SC2034  # accepted for backward compatibility, now in the profile
THRESHOLDS="${2:-thresholds.yml}"
DURATION="${3:-30s}"
INTERVAL="${4:-5s}"
OUTDIR="${5:-runs/gate-$(date +%Y%m%dT%H%M%S)}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

set +e
python3 -m aipreflight.cli check \
    --profile "$REPO_ROOT/profiles/inference.yml" \
    --config "$CONFIG" \
    --duration "$DURATION" \
    --interval "$INTERVAL" \
    --out "$OUTDIR"
EXIT_CODE=$?
set -e

echo ""
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "GATE: PASS"
else
    echo "GATE: FAIL"
    echo "Diagnose: aipreflight diagnose $OUTDIR --prometheus http://localhost:9090"
fi

exit "$EXIT_CODE"
