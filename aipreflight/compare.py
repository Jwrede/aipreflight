"""Compare readiness across concurrency levels from a sweep run."""

import json
import sys
from pathlib import Path

from aipreflight.metrics import format_ms, percentile

__all__ = ["analyze_run", "percentile", "format_ms", "main"]


def analyze_run(jsonl_path: Path) -> dict:
    probes = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if line:
                probes.append(json.loads(line))

    ttfts = [p["ttft_ms"] for p in probes if p.get("ttft_ms") is not None]
    latencies = [p["latency_ms"] for p in probes if p.get("latency_ms") is not None]
    throughputs = [p["tokens_per_sec"] for p in probes if p.get("tokens_per_sec") is not None]
    errors = sum(1 for p in probes if p.get("status") == "error")

    return {
        "total": len(probes),
        "errors": errors,
        "error_rate": errors / len(probes) if probes else 0,
        "ttft_p50": percentile(ttfts, 50),
        "ttft_p95": percentile(ttfts, 95),
        "latency_p50": percentile(latencies, 50),
        "latency_p95": percentile(latencies, 95),
        "throughput_p50": percentile(throughputs, 50),
        "throughput_min": min(throughputs) if throughputs else 0,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: compare.py <sweep-dir>", file=sys.stderr)
        sys.exit(1)

    sweep_dir = Path(sys.argv[1])
    runs = sorted(sweep_dir.glob("c*/llmprobe.jsonl"))

    if not runs:
        print("No run data found.", file=sys.stderr)
        sys.exit(1)

    results = []
    for run_path in runs:
        concurrency = run_path.parent.name.replace("c", "")
        analysis = analyze_run(run_path)
        analysis["concurrency"] = int(concurrency)
        results.append(analysis)

    results.sort(key=lambda r: r["concurrency"])

    lines = []
    lines.append("# Concurrency Sweep Comparison")
    lines.append("")
    lines.append("| Concurrency | TTFT p50 | TTFT p95 | Latency p50 | Latency p95 | Throughput p50 | Error Rate |")
    lines.append("|-------------|----------|----------|-------------|-------------|----------------|------------|")

    for r in results:
        lines.append(
            f"| {r['concurrency']} "
            f"| {format_ms(r['ttft_p50'])} "
            f"| {format_ms(r['ttft_p95'])} "
            f"| {format_ms(r['latency_p50'])} "
            f"| {format_ms(r['latency_p95'])} "
            f"| {r['throughput_p50']:.1f} tok/s "
            f"| {r['error_rate']:.0%} |"
        )

    lines.append("")
    lines.append("## Observations")
    lines.append("")

    if len(results) >= 2:
        first = results[0]
        last = results[-1]
        ttft_ratio = last["ttft_p95"] / first["ttft_p95"] if first["ttft_p95"] > 0 else 0
        if ttft_ratio > 3:
            lines.append(
                f"- TTFT p95 increased {ttft_ratio:.1f}x from concurrency "
                f"{first['concurrency']} to {last['concurrency']}. "
                "Likely saturating compute or hitting queue backpressure."
            )
        if last["error_rate"] > 0.05 and first["error_rate"] == 0:
            lines.append(
                f"- Errors appeared at concurrency {last['concurrency']} "
                f"({last['error_rate']:.0%}). Server may be rejecting requests under load."
            )
        if last["throughput_p50"] < first["throughput_p50"] * 0.5:
            lines.append(
                "- Per-request throughput dropped significantly under load. "
                "Batch scheduling may be contending for memory."
            )

    lines.append("")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
