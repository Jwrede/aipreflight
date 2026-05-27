"""Build readiness reports from analyzed probe data.

generate_report() produces the original standalone Markdown report (kept for the
scripts/report.py wrapper). build_report()/write_reports() produce the unified
JSON + Markdown artifacts emitted by `aipreflight check`, leading with a blunt
PASS / FAIL / WARN verdict.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from aipreflight.analyze import analyze, check_gate, verdict_from_analysis
from aipreflight.checks import FAIL, WARN, CheckResult, aggregate_verdict
from aipreflight.metrics import format_ms, percentile


def _verdict(analysis: dict, thresholds: dict) -> tuple[str, list[str], list[str]]:
    """Return (PASS|FAIL|WARN, failed_checks, warnings)."""
    passed, violations = check_gate(analysis, thresholds)
    if not passed:
        return "FAIL", violations, []

    warnings = []
    total = analysis["total"]
    degraded = analysis["statuses"].get("degraded", 0)
    if total and degraded:
        warnings.append(
            f"{degraded}/{total} probes degraded ({degraded / total:.0%}). "
            "Within gate, but worth watching under load."
        )
    return ("WARN" if warnings else "PASS"), [], warnings


def build_report(
    probes: list[dict],
    profile: dict,
    source_path: str,
    artifacts: dict | None = None,
) -> dict:
    """Build the machine-readable readiness report dict."""
    analysis = analyze(probes)
    thresholds = profile["thresholds"]
    verdict, failed, warnings = _verdict(analysis, thresholds)
    total = analysis["total"]

    metrics = {
        "total_probes": total,
        "statuses": analysis["statuses"],
        "ttft_ms_p95": percentile(analysis["ttfts"], 95) if analysis["ttfts"] else None,
        "latency_ms_p95": percentile(analysis["latencies"], 95) if analysis["latencies"] else None,
        "throughput_p50": percentile(analysis["throughputs"], 50) if analysis["throughputs"] else None,
        "error_rate": (analysis["statuses"].get("error", 0) / total) if total else None,
    }

    return {
        "verdict": verdict,
        "profile": profile["name"],
        "kind": profile.get("kind", "inference"),
        "generated": datetime.now(timezone.utc).isoformat(),
        "source": source_path,
        "failed_checks": failed,
        "warnings": warnings,
        "metrics": metrics,
        "thresholds": thresholds,
        "artifacts": artifacts or {},
    }


def build_app_report(results: list[CheckResult], profile: dict, artifacts: dict | None = None) -> dict:
    """Build the readiness report dict for an app-kind profile."""
    return {
        "verdict": aggregate_verdict(results),
        "profile": profile["name"],
        "kind": "app",
        "generated": datetime.now(timezone.utc).isoformat(),
        "checks": [r.to_dict() for r in results],
        "failed_checks": [r.summary for r in results if r.status == FAIL],
        "warnings": [r.summary for r in results if r.status == WARN],
        "artifacts": artifacts or {},
    }


def _render_app_markdown(report: dict) -> str:
    lines = []
    lines.append(f"# aipreflight: {report['verdict']}")
    lines.append("")
    lines.append(f"Profile: `{report['profile']}` (kind: app)")
    lines.append(f"Generated: {report['generated']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Status | Summary |")
    lines.append("|-------|--------|---------|")
    for c in report["checks"]:
        lines.append(f"| {c['name']} | {c['status']} | {c['summary']} |")
    lines.append("")
    if report["failed_checks"]:
        lines.append("## Failed checks")
        lines.append("")
        for v in report["failed_checks"]:
            lines.append(f"- {v}")
        lines.append("")
    if report["warnings"]:
        lines.append("## Warnings")
        lines.append("")
        for w in report["warnings"]:
            lines.append(f"- {w}")
        lines.append("")
    lines.append("## Recommended action")
    lines.append("")
    if report["verdict"] == "PASS":
        lines.append("- Safe to ship. All configured readiness checks pass.")
    elif report["verdict"] == "WARN":
        lines.append("- Acceptable to ship, but resolve the warnings above soon.")
    else:
        lines.append("- Do not ship. Resolve the failed checks above first.")
    lines.append("")
    return "\n".join(lines)


def render_markdown(report: dict) -> str:
    """Render the unified report dict as Markdown, verdict first."""
    if "checks" in report:
        return _render_app_markdown(report)
    m = report["metrics"]
    sla = report["thresholds"].get("sla", {})
    lines = []
    lines.append(f"# aipreflight: {report['verdict']}")
    lines.append("")
    lines.append(f"Profile: `{report['profile']}`")
    lines.append(f"Generated: {report['generated']}")
    lines.append(f"Probes: {m['total_probes']}")
    lines.append("")

    if report["failed_checks"]:
        lines.append("## Failed checks")
        lines.append("")
        for v in report["failed_checks"]:
            lines.append(f"- {v}")
        lines.append("")
    if report["warnings"]:
        lines.append("## Warnings")
        lines.append("")
        for w in report["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("## SLA checks")
    lines.append("")
    lines.append("| Metric | Threshold | Observed | Status |")
    lines.append("|--------|-----------|----------|--------|")
    if sla.get("ttft_ms") and m["ttft_ms_p95"] is not None:
        ok = m["ttft_ms_p95"] <= sla["ttft_ms"]
        lines.append(f"| TTFT p95 | {format_ms(sla['ttft_ms'])} | {format_ms(m['ttft_ms_p95'])} | {'PASS' if ok else 'FAIL'} |")
    if sla.get("latency_ms") and m["latency_ms_p95"] is not None:
        ok = m["latency_ms_p95"] <= sla["latency_ms"]
        lines.append(f"| Latency p95 | {format_ms(sla['latency_ms'])} | {format_ms(m['latency_ms_p95'])} | {'PASS' if ok else 'FAIL'} |")
    if sla.get("min_throughput") and m["throughput_p50"] is not None:
        ok = m["throughput_p50"] >= sla["min_throughput"]
        lines.append(f"| Throughput p50 | >={sla['min_throughput']:.1f} tok/s | {m['throughput_p50']:.1f} tok/s | {'PASS' if ok else 'FAIL'} |")
    if sla.get("max_error_rate") is not None and m["error_rate"] is not None:
        ok = m["error_rate"] <= sla["max_error_rate"]
        lines.append(f"| Error rate | <={sla['max_error_rate']:.0%} | {m['error_rate']:.0%} | {'PASS' if ok else 'FAIL'} |")
    lines.append("")

    lines.append("## Endpoint health")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    for status in ["healthy", "degraded", "error"]:
        lines.append(f"| {status} | {report['metrics']['statuses'].get(status, 0)} |")
    lines.append("")

    lines.append("## Recommended action")
    lines.append("")
    if report["verdict"] == "PASS":
        lines.append("- Safe to route traffic. No action needed.")
    elif report["verdict"] == "WARN":
        lines.append("- Acceptable to ship, but monitor the warnings above under real load.")
    else:
        lines.append("- Do not route production traffic.")
        lines.append("- Run `aipreflight diagnose runs/latest --prometheus <url>` to find the cause.")
    lines.append("")
    return "\n".join(lines)


def write_reports(report: dict, out_dir: Path) -> dict:
    """Write JSON + Markdown reports into out_dir. Returns artifact paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "aipreflight-report.json"
    md_path = out_dir / "aipreflight-report.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(render_markdown(report))
    return {"json": str(json_path), "markdown": str(md_path)}


def generate_report(probes: list[dict], source_path: str, thresholds: dict | None = None) -> str:
    """Original standalone Markdown report (used by scripts/report.py)."""
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
        lines.append("- Consider running `aipreflight diagnose` with Prometheus for deeper visibility.")
    elif verdict == "NOT READY":
        lines.append("- Do not route production traffic.")
        lines.append("- Run `aipreflight diagnose runs/latest` to correlate with server metrics.")
        lines.append("- Check: model loading status, resource limits, network path.")
    else:
        lines.append("- Monitor TTFT and latency trends under load.")
        lines.append("- Run `aipreflight diagnose runs/latest` for root cause analysis.")
        lines.append("- Consider reducing concurrency or scaling resources.")
    lines.append("")

    return "\n".join(lines)
