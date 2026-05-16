#!/usr/bin/env python3
"""Diagnose inference issues by correlating llmprobe data with vLLM Prometheus metrics.

Usage:
  diagnose.py <probes.jsonl>                              # Client-only analysis
  diagnose.py <probes.jsonl> --prometheus-data metrics.json  # Full correlation
  diagnose.py <probes.jsonl> --prometheus http://localhost:9090  # Live query
"""

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote

import yaml


def load_probes(path: str) -> list[dict]:
    probes = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                probes.append(json.loads(line))
    return probes


def load_queries(path: str = "configs/prometheus/queries.yml") -> dict:
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("queries", {})


def query_prometheus(endpoint: str, expr: str, start: str, end: str) -> list[dict]:
    """Query Prometheus range API."""
    params = f"query={quote(expr)}&start={start}&end={end}&step=15s"
    url = f"{endpoint}/api/v1/query_range?{params}"
    try:
        req = Request(url)
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("status") == "success":
                return data.get("data", {}).get("result", [])
            err = data.get("error", "")
            if err:
                print(f"  Warning: Prometheus error for {expr[:40]}: {err}", file=sys.stderr)
    except (URLError, json.JSONDecodeError) as e:
        print(f"  Warning: Prometheus query failed: {e}", file=sys.stderr)
    return []


def collect_server_metrics(endpoint: str, probes: list[dict], queries: dict) -> dict:
    """Collect server-side metrics for the probe time window."""
    timestamps = [p.get("timestamp", "") for p in probes if p.get("timestamp")]
    if not timestamps:
        return {}

    start = min(timestamps)
    end = max(timestamps)

    metrics = {}
    for name, q in queries.items():
        results = query_prometheus(endpoint, q["expr"], start, end)
        if results:
            values = []
            for series in results:
                for ts, val in series.get("values", []):
                    try:
                        v = float(val)
                        if not math.isnan(v) and not math.isinf(v):
                            values.append(v)
                    except (ValueError, TypeError):
                        pass
            if values:
                metrics[name] = {
                    "mean": sum(values) / len(values),
                    "max": max(values),
                    "min": min(values),
                    "unit": q.get("unit", ""),
                    "description": q.get("description", ""),
                }
    return metrics


def load_metrics_file(path: str) -> dict:
    """Load pre-collected Prometheus metrics from JSON."""
    with open(path) as f:
        return json.load(f)


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


def diagnose(probes: list[dict], server_metrics: dict | None = None) -> str:
    """Produce a diagnosis report."""
    lines = []
    lines.append("# Inference Diagnosis")
    lines.append("")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"Generated: {now}")
    lines.append(f"Probes analyzed: {len(probes)}")
    lines.append("")

    ttfts = [p["ttft_ms"] for p in probes if p.get("ttft_ms") is not None]
    latencies = [p["latency_ms"] for p in probes if p.get("latency_ms") is not None]
    errors = [p for p in probes if p.get("status") == "error"]
    degraded = [p for p in probes if p.get("status") == "degraded"]

    lines.append("## Client-Side Observations")
    lines.append("")
    if ttfts:
        lines.append(f"- TTFT p50: {format_ms(percentile(ttfts, 50))}, p95: {format_ms(percentile(ttfts, 95))}")
    if latencies:
        lines.append(f"- Latency p50: {format_ms(percentile(latencies, 50))}, p95: {format_ms(percentile(latencies, 95))}")
    lines.append(f"- Errors: {len(errors)}/{len(probes)} ({len(errors)/len(probes):.0%})")
    lines.append(f"- Degraded: {len(degraded)}/{len(probes)} ({len(degraded)/len(probes):.0%})")
    lines.append("")

    if server_metrics:
        lines.append("## Server-Side Metrics")
        lines.append("")
        lines.append("| Metric | Mean | Max | Unit |")
        lines.append("|--------|------|-----|------|")
        for name, m in server_metrics.items():
            lines.append(f"| {m.get('description', name)} | {m['mean']:.3f} | {m['max']:.3f} | {m['unit']} |")
        lines.append("")

        lines.append("## Correlation Analysis")
        lines.append("")

        server_ttft = server_metrics.get("ttft")
        if server_ttft and ttfts:
            server_ttft_ms = server_ttft["mean"] * 1000
            client_ttft_ms = percentile(ttfts, 95)
            gap = client_ttft_ms - server_ttft_ms
            if gap > 100:
                lines.append(
                    f"- **Network/proxy overhead detected**: Client TTFT p95 ({format_ms(client_ttft_ms)}) "
                    f"exceeds server TTFT p95 ({format_ms(server_ttft_ms)}) by {format_ms(gap)}. "
                    "Check load balancer, TLS termination, or DNS resolution."
                )
            else:
                lines.append(
                    f"- Client and server TTFT p95 align (gap: {format_ms(abs(gap))}). "
                    "No significant network overhead."
                )

        queue = server_metrics.get("queue_depth")
        if queue and queue["max"] > 5:
            lines.append(
                f"- **Queue pressure**: Max queue depth {queue['max']:.0f}. "
                "Requests are waiting for inference slots. Scale replicas or reduce concurrency."
            )

        kv = server_metrics.get("kv_cache_usage")
        if kv and kv["max"] > 0.8:
            lines.append(
                f"- **KV cache pressure**: Peak usage {kv['max']:.0%}. "
                "Long sequences may be evicted, causing recomputation and TTFT spikes."
            )

        if not any([
            server_ttft and ttfts and (percentile(ttfts, 95) - server_ttft["mean"] * 1000) > 100,
            queue and queue["max"] > 5,
            kv and kv["max"] > 0.8,
        ]):
            lines.append("- No significant issues detected in server metrics.")

        lines.append("")
    else:
        lines.append("## Server-Side Metrics")
        lines.append("")
        lines.append("Not available. To enable correlation analysis:")
        lines.append("```bash")
        lines.append("python3 scripts/diagnose.py probes.jsonl --prometheus http://localhost:9090")
        lines.append("```")
        lines.append("")

    lines.append("## Possible Causes")
    lines.append("")
    if errors:
        error_msgs = set(p.get("error", "unknown") for p in errors)
        for msg in list(error_msgs)[:5]:
            if "connection" in msg.lower():
                lines.append(f"- **Connection failure** (`{msg}`): Server may be down, overloaded, or unreachable.")
            elif "timeout" in msg.lower():
                lines.append(f"- **Timeout** (`{msg}`): Server too slow to respond within deadline.")
            else:
                lines.append(f"- **Error** (`{msg}`): Investigate server logs.")

    if degraded and ttfts:
        high_ttft = [p["ttft_ms"] for p in degraded if p.get("ttft_ms")]
        if high_ttft and percentile(high_ttft, 50) > 2000:
            lines.append("- **TTFT degradation during probe window**: Possible causes:")
            lines.append("  - Model prefill contention (too many concurrent long prompts)")
            lines.append("  - KV cache eviction forcing recomputation")
            lines.append("  - Batch scheduler starvation")

    if not errors and not degraded:
        lines.append("- No issues detected. Endpoint is healthy.")

    lines.append("")
    lines.append("## Recommended Actions")
    lines.append("")
    if errors:
        lines.append("1. Verify endpoint connectivity and model loading status.")
        lines.append("2. Check server resource limits (CPU, memory, GPU memory).")
        lines.append("3. Review server logs for OOM or CUDA errors.")
    elif degraded:
        lines.append("1. Run a concurrency sweep to find the saturation point:")
        lines.append("   ```bash")
        lines.append("   ./scripts/sweep.sh configs/llmprobe/vllm.yml 1,2,4,8")
        lines.append("   ```")
        lines.append("2. If Prometheus available, check queue depth and KV cache:")
        lines.append("   ```bash")
        lines.append("   python3 scripts/diagnose.py probes.jsonl --prometheus http://localhost:9090")
        lines.append("   ```")
        lines.append("3. Consider reducing max concurrent requests or increasing replicas.")
    else:
        lines.append("- No action needed. Consider periodic monitoring with `llmprobe watch`.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Diagnose LLM inference issues")
    parser.add_argument("probes", help="Path to llmprobe JSONL file")
    parser.add_argument("--prometheus", help="Prometheus endpoint URL for live queries")
    parser.add_argument("--prometheus-data", help="Pre-collected Prometheus metrics JSON file")
    parser.add_argument("--queries", default="configs/prometheus/queries.yml", help="Prometheus queries file")
    args = parser.parse_args()

    probes = load_probes(args.probes)

    server_metrics = None
    if args.prometheus:
        queries = load_queries(args.queries)
        server_metrics = collect_server_metrics(args.prometheus, probes, queries)
    elif args.prometheus_data:
        server_metrics = load_metrics_file(args.prometheus_data)

    report = diagnose(probes, server_metrics)
    print(report)


if __name__ == "__main__":
    main()
