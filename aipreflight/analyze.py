"""Analyze probe data and evaluate it against SLA thresholds."""

from aipreflight.metrics import format_ms, percentile
from aipreflight.probes import load_probes

__all__ = [
    "analyze",
    "check_gate",
    "verdict_from_analysis",
    "load_probes",
    "percentile",
    "format_ms",
]


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
