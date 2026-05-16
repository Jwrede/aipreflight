#!/usr/bin/env bash
# Replay realistic gate + diagnose output for demo recording

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

slow() { echo "$@" | while IFS= read -r line; do echo "$line"; sleep 0.08; done; }

echo -e "${BOLD}$ ./scripts/gate.sh configs/llmprobe/vllm.yml thresholds.yml 30s 5s${NC}"
sleep 0.5

slow "Running readiness gate...
  Config:     configs/llmprobe/vllm.yml
  Thresholds: thresholds.yml
  Duration:   30s
  Interval:   5s"
sleep 0.3

echo ""
slow "Collected 6 probes."
echo ""
sleep 0.3

echo -e "${GREEN}PASS: All SLA thresholds met.${NC}"
echo ""
echo -e "${GREEN}GATE: PASS${NC}"
sleep 1.5

echo ""
echo -e "${BOLD}$ python3 scripts/diagnose.py runs/latest/llmprobe.jsonl --prometheus http://localhost:9090${NC}"
sleep 0.5

slow "# Inference Diagnosis

Generated: 2026-05-16 21:35 UTC
Probes analyzed: 240"
echo ""

slow "## Client-Side Observations

- TTFT p50: 458ms, p95: 941ms
- Latency p50: 1.60s, p95: 3.11s
- Errors: 0/240 (0%)
- Degraded: 0/240 (0%)"
echo ""

slow "## Server-Side Metrics

| Metric | Mean | Max | Unit |
|--------|------|-----|------|"
echo -e "| Server-reported TTFT p95 | 0.912 | ${YELLOW}0.942${NC} | seconds |"
sleep 0.05
echo "| Requests currently running | 13.500 | 16.000 | count |"
sleep 0.05
echo "| KV cache utilization | 0.017 | 0.021 | percent |"
echo ""

slow "## Correlation Analysis"
echo ""
echo -e "- Client and server TTFT p95 align (gap: ${GREEN}29ms${NC}). No significant network overhead."
echo ""

slow "## Recommended Actions

- No action needed. Consider periodic monitoring with llmprobe watch."
echo ""
sleep 2
