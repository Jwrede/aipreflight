#!/usr/bin/env python3
"""Generate readiness verdicts from llmprobe JSONL output.

Two modes:
  report.py <probes.jsonl>                        Full Markdown report
  report.py --gate --thresholds t.yml <probes>    Exit 0 if pass, 1 if fail
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def load_probes(path: str) -> list[dict]:
    probes = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                probes.append(json.loads(line))
    return probes


def load_thresholds(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = min(int(len(sorted_vals) * p / 100), len(sorted_vals) - 1)
    return sorted_vals[idx]


def format_ms(ms: float) -> str:
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms / 1000:.2f}s"


def analyze(probes: list[dict]) -> dict:
    ttfts = []
    latencies = []
    throughputs = []
    errors = []
    statuses = {"healthy": 0, "degraded": 0, "error": 0}

    for p in probes:
        status = p.get("status", "unknown")
        statuses[status] = statuses.get(status, 0) + 1

        if status == "error":
            errors.append(p)
            continue

        if p.get("ttft_ms") is not None:
            ttfts.append(p["ttft_ms"])
        if p.get("latency_ms") is not None:
            latencies.append(p["latency_ms"])
        if p.get("tokens_per_sec") is not None:
            throughputs.append(p["tokens_per_sec"])

    return {
        "total": len(probes),
        "statuses": statuses,
        "ttfts": ttfts,
        "latencies": latencies,
        "throughputs": throughputs,
        "errors": errors,
    }


def check_gate(analysis: dict, thresholds: dict) -> tuple[bool, list[str]]:
    """Check if probes pass SLA thresholds. Returns (passed, violations)."""
    sla = thresholds.get("sla", {})
    gate = thresholds.get("gate", {})
    violations = []

    total = analysis["total"]
    min_probes = gate.get("min_probes", 5)
    if total < min_probes:
        return False, [f"Insufficient data: {total} probes (need {min_probes})"]

    pass_rate_threshold = gate.get("pass_rate", 0.95)
    healthy = analysis["statuses"].get("healthy", 0)
    pass_rate = healthy / total
    if pass_rate < pass_rate_threshold:
        violations.append(
            f"Pass rate {pass_rate:.0%} below {pass_rate_threshold:.0%} threshold"
        )

    ttft_limit = sla.get("ttft_ms")
    if ttft_limit and analysis["ttfts"]:
        ttft_p95 = percentile(analysis["ttfts"], 95)
        if ttft_p95 > ttft_limit:
            violations.append(
                f"TTFT p95 {format_ms(ttft_p95)} exceeds {format_ms(ttft_limit)} SLA"
            )

    latency_limit = sla.get("latency_ms")
    if latency_limit and analysis["latencies"]:
        lat_p95 = percentile(analysis["latencies"], 95)
        if lat_p95 > latency_limit:
            violations.append(
                f"Latency p95 {format_ms(lat_p95)} exceeds {format_ms(latency_limit)} SLA"
            )

    min_tput = sla.get("min_throughput")
    if min_tput and analysis["throughputs"]:
        tput_p50 = percentile(analysis["throughputs"], 50)
        if tput_p50 < min_tput:
            violations.append(
                f"Throughput p50 {tput_p50:.1f} tok/s below {min_tput:.1f} minimum"
            )

    max_err = sla.get("max_error_rate", 0.01)
    error_rate = analysis["statuses"].get("error", 0) / total
    if error_rate > max_err:
        violations.append(
            f"Error rate {error_rate:.0%} exceeds {max_err:.0%} threshold"
        )

    return len(violations) == 0, violations


def verdict_from_analysis(analysis: dict, thresholds: dict | None) -> tuple[str, str]:
    """Produce a verdict string."""
    if thresholds:
        passed, violations = check_gate(analysis, thresholds)
        if passed:
            return "READY", "All SLA thresholds met. Safe to route traffic."
        return "NOT READY", " | ".join(violations)

    total = analysis["total"]
    if total == 0:
        return "UNKNOWN", "No probe data available."

    error_rate = analysis["statuses"].get("error", 0) / total
    degraded_rate = analysis["statuses"].get("degraded", 0) / total

    if error_rate > 0.1:
        return "NOT READY", f"Error rate {error_rate:.0%} exceeds 10%."
    if error_rate > 0 or degraded_rate > 0.2:
        return "DEGRADED", (
            f"Error rate {error_rate:.0%}, degraded rate {degraded_rate:.0%}. "
            "Investigate before serving production traffic."
        )
    if degraded_rate > 0:
        return "READY WITH WARNINGS", (
            f"Degraded rate {degraded_rate:.0%}. "
            "Acceptable for non-critical workloads."
        )
    return "READY", "All probes healthy. Safe to serve traffic."


def generate_report(probes: list[dict], source_path: str, thresholds: dict | None = None) -> str:
    analysis = analyze(probes)
    verdict, reason = verdict_from_analysis(analysis, thresholds)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append("# Inference Readiness Report")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append(f"Source: `{source_path}`")
    lines.append(f"Total probes: {analysis['total']}")
    lines.append("")

    lines.append("## Verdict")
    lines.append("")
    lines.append(f"**{verdict}**")
    lines.append("")
    lines.append(reason)
    lines.append("")

    if thresholds:
        sla = thresholds.get("sla", {})
        lines.append("## SLA Thresholds")
        lines.append("")
        lines.append("| Metric | Threshold | Observed (p95) | Status |")
        lines.append("|--------|-----------|----------------|--------|")
        if sla.get("ttft_ms") and analysis["ttfts"]:
            obs = percentile(analysis["ttfts"], 95)
            ok = obs <= sla["ttft_ms"]
            lines.append(f"| TTFT | {format_ms(sla['ttft_ms'])} | {format_ms(obs)} | {'PASS' if ok else 'FAIL'} |")
        if sla.get("latency_ms") and analysis["latencies"]:
            obs = percentile(analysis["latencies"], 95)
            ok = obs <= sla["latency_ms"]
            lines.append(f"| Latency | {format_ms(sla['latency_ms'])} | {format_ms(obs)} | {'PASS' if ok else 'FAIL'} |")
        if sla.get("min_throughput") and analysis["throughputs"]:
            obs = percentile(analysis["throughputs"], 50)
            ok = obs >= sla["min_throughput"]
            lines.append(f"| Throughput | >={sla['min_throughput']:.1f} tok/s | {obs:.1f} tok/s | {'PASS' if ok else 'FAIL'} |")
        if sla.get("max_error_rate"):
            obs = analysis["statuses"].get("error", 0) / analysis["total"]
            ok = obs <= sla["max_error_rate"]
            lines.append(f"| Error rate | <={sla['max_error_rate']:.0%} | {obs:.0%} | {'PASS' if ok else 'FAIL'} |")
        lines.append("")

    lines.append("## Endpoint Health")
    lines.append("")
    lines.append("| Status | Count | Rate |")
    lines.append("|--------|-------|------|")
    for status in ["healthy", "degraded", "error"]:
        count = analysis["statuses"].get(status, 0)
        rate = count / analysis["total"] if analysis["total"] > 0 else 0
        lines.append(f"| {status} | {count} | {rate:.0%} |")
    lines.append("")

    if analysis["ttfts"]:
        lines.append("## Time to First Token (TTFT)")
        lines.append("")
        lines.append("| Percentile | Value |")
        lines.append("|------------|-------|")
        lines.append(f"| p50 | {format_ms(percentile(analysis['ttfts'], 50))} |")
        lines.append(f"| p95 | {format_ms(percentile(analysis['ttfts'], 95))} |")
        lines.append(f"| p99 | {format_ms(percentile(analysis['ttfts'], 99))} |")
        lines.append("")

    if analysis["latencies"]:
        lines.append("## Latency")
        lines.append("")
        lines.append("| Percentile | Value |")
        lines.append("|------------|-------|")
        lines.append(f"| p50 | {format_ms(percentile(analysis['latencies'], 50))} |")
        lines.append(f"| p95 | {format_ms(percentile(analysis['latencies'], 95))} |")
        lines.append(f"| p99 | {format_ms(percentile(analysis['latencies'], 99))} |")
        lines.append("")

    if analysis["throughputs"]:
        lines.append("## Throughput")
        lines.append("")
        lines.append("| Percentile | Value |")
        lines.append("|------------|-------|")
        lines.append(f"| p50 | {percentile(analysis['throughputs'], 50):.1f} tok/s |")
        lines.append(f"| p95 | {percentile(analysis['throughputs'], 95):.1f} tok/s |")
        lines.append(f"| min | {min(analysis['throughputs']):.1f} tok/s |")
        lines.append("")

    if analysis["errors"]:
        lines.append("## Errors")
        lines.append("")
        for e in analysis["errors"][:5]:
            model = e.get("model", "unknown")
            msg = e.get("error", "no message")
            lines.append(f"- **{model}**: {msg}")
        if len(analysis["errors"]) > 5:
            lines.append(f"- ... and {len(analysis['errors']) - 5} more")
        lines.append("")

    lines.append("## Next Steps")
    lines.append("")
    if verdict == "READY":
        lines.append("- Endpoint is healthy. No immediate action needed.")
        lines.append("- Consider running `scripts/diagnose.py` with Prometheus for deeper visibility.")
    elif verdict == "NOT READY":
        lines.append("- Do not route production traffic.")
        lines.append("- Run `python3 scripts/diagnose.py <probes.jsonl>` to correlate with server metrics.")
        lines.append("- Check: model loading status, resource limits, network path.")
    else:
        lines.append("- Monitor TTFT and latency trends under load.")
        lines.append("- Run `python3 scripts/diagnose.py <probes.jsonl>` for root cause analysis.")
        lines.append("- Consider reducing concurrency or scaling resources.")
    lines.append("")

    return "\n".join(lines)


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
        else:
            print("FAIL: SLA violations detected:")
            for v in violations:
                print(f"  - {v}")
            sys.exit(1)

    report = generate_report(probes, args.probes, thresholds)
    print(report)


if __name__ == "__main__":
    main()
