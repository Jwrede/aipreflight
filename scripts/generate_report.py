#!/usr/bin/env python3
"""Generate a readiness report from llmprobe JSONL output."""

import json
import sys
import statistics
from datetime import datetime, timezone
from pathlib import Path


def load_probes(path: str) -> list[dict]:
    probes = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                probes.append(json.loads(line))
    return probes


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * p / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


def format_duration(ms: float) -> str:
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

        if "ttft_ms" in p and p["ttft_ms"] is not None:
            ttfts.append(p["ttft_ms"])
        if "latency_ms" in p and p["latency_ms"] is not None:
            latencies.append(p["latency_ms"])
        if "tokens_per_sec" in p and p["tokens_per_sec"] is not None:
            throughputs.append(p["tokens_per_sec"])

    return {
        "total": len(probes),
        "statuses": statuses,
        "ttfts": ttfts,
        "latencies": latencies,
        "throughputs": throughputs,
        "errors": errors,
    }


def readiness_judgment(analysis: dict) -> tuple[str, str]:
    total = analysis["total"]
    if total == 0:
        return "UNKNOWN", "No probe data available."

    error_rate = analysis["statuses"].get("error", 0) / total
    degraded_rate = analysis["statuses"].get("degraded", 0) / total

    if error_rate > 0.1:
        return "NOT READY", f"Error rate {error_rate:.0%} exceeds 10% threshold."
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


def generate_report(probes: list[dict], source_path: str) -> str:
    analysis = analyze(probes)
    judgment, reason = readiness_judgment(analysis)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append("# Inference Readiness Report")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append(f"Source: `{source_path}`")
    lines.append(f"Total probes: {analysis['total']}")
    lines.append("")

    lines.append("## Readiness Judgment")
    lines.append("")
    lines.append(f"**{judgment}**")
    lines.append("")
    lines.append(reason)
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
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| p50 | {format_duration(percentile(analysis['ttfts'], 50))} |")
        lines.append(f"| p95 | {format_duration(percentile(analysis['ttfts'], 95))} |")
        lines.append(f"| p99 | {format_duration(percentile(analysis['ttfts'], 99))} |")
        lines.append(f"| min | {format_duration(min(analysis['ttfts']))} |")
        lines.append(f"| max | {format_duration(max(analysis['ttfts']))} |")
        lines.append("")

    if analysis["latencies"]:
        lines.append("## Latency")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| p50 | {format_duration(percentile(analysis['latencies'], 50))} |")
        lines.append(f"| p95 | {format_duration(percentile(analysis['latencies'], 95))} |")
        lines.append(f"| p99 | {format_duration(percentile(analysis['latencies'], 99))} |")
        lines.append(f"| min | {format_duration(min(analysis['latencies']))} |")
        lines.append(f"| max | {format_duration(max(analysis['latencies']))} |")
        lines.append("")

    if analysis["throughputs"]:
        lines.append("## Throughput")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| p50 | {percentile(analysis['throughputs'], 50):.1f} tok/s |")
        lines.append(f"| p95 | {percentile(analysis['throughputs'], 95):.1f} tok/s |")
        lines.append(f"| min | {min(analysis['throughputs']):.1f} tok/s |")
        lines.append(f"| max | {max(analysis['throughputs']):.1f} tok/s |")
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
    if judgment == "READY":
        lines.append("- Endpoint is healthy. No immediate action needed.")
        lines.append("- Consider adding server-side metrics (Prometheus) for deeper visibility.")
    elif judgment == "NOT READY":
        lines.append("- Investigate error causes before serving traffic.")
        lines.append("- Check: API connectivity, model loading status, resource limits.")
        lines.append("- Re-run probes after fixes to confirm resolution.")
    else:
        lines.append("- Monitor TTFT and latency trends under load.")
        lines.append("- Add server-side metrics to correlate with queue depth and KV cache.")
        lines.append("- Consider reducing concurrency or scaling resources.")
    lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_report.py <llmprobe.jsonl>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    probes = load_probes(path)
    report = generate_report(probes, path)
    print(report)


if __name__ == "__main__":
    main()
