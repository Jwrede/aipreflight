#!/usr/bin/env python3
"""Compatibility wrapper around the aipreflight package.

Prefer `aipreflight check --profile profiles/inference.yml`. This script is kept
so existing commands keep working.

  report.py <probes.jsonl>                       Full Markdown report
  report.py --gate --thresholds t.yml <probes>   Exit 0 if pass, 1 if fail
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from aipreflight.analyze import analyze, check_gate, load_probes  # noqa: E402
from aipreflight.report import generate_report  # noqa: E402


def load_thresholds(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="LLM inference readiness report")
    parser.add_argument("probes", help="Path to llmprobe JSONL file")
    parser.add_argument("--gate", action="store_true", help="Gate mode: exit 1 if thresholds violated")
    parser.add_argument("--thresholds", help="Path to thresholds YAML file")
    args = parser.parse_args()

    probes = load_probes(args.probes)
    thresholds = load_thresholds(args.thresholds) if args.thresholds else None

    if args.gate:
        if not thresholds:
            print("Error: --gate requires --thresholds", file=sys.stderr)
            sys.exit(2)
        analysis = analyze(probes)
        passed, violations = check_gate(analysis, thresholds)
        if passed:
            print("PASS: All SLA thresholds met.")
            sys.exit(0)
        print("FAIL: SLA violations detected:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)

    print(generate_report(probes, args.probes, thresholds))


if __name__ == "__main__":
    main()
