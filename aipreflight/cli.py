"""aipreflight command-line interface.

Subcommands:
  check     run a readiness check against a profile and emit a verdict + report
  report    re-render the Markdown report for a completed run
  diagnose  correlate probe data with server-side Prometheus metrics

Exit codes:
  0  readiness pass (PASS or WARN)
  1  readiness fail (FAIL)
  2  invalid config or missing dependency
  3  probe/eval execution error
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from aipreflight import EXIT_CONFIG, EXIT_FAIL, EXIT_PASS, EXIT_PROBE
from aipreflight import report as report_mod
from aipreflight.diagnose import (
    collect_server_metrics,
    diagnose,
    load_metrics_file,
    load_queries,
)
from aipreflight.probes import MissingDependency, ProbeError, load_probes, run_llmprobe
from aipreflight.profile import ProfileError, load_profile


def _err(msg: str) -> None:
    print(f"aipreflight: {msg}", file=sys.stderr)


def _run_dir(profile: dict, out: str | None) -> Path:
    if out:
        return Path(out)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return Path(profile["report"]["outdir"]) / f"{profile['name']}-{stamp}"


def _update_latest(run_dir: Path) -> None:
    """Point <outdir>/latest at the run dir, best effort."""
    latest = run_dir.parent / "latest"
    try:
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(run_dir.name)
    except OSError:
        pass


def cmd_check(args: argparse.Namespace) -> int:
    try:
        profile = load_profile(args.profile)
    except ProfileError as e:
        _err(str(e))
        return EXIT_CONFIG

    if profile["kind"] == "app":
        return _check_app(args, profile)
    return _check_inference(args, profile)


def _emit(report: dict, artifacts: dict) -> int:
    print(f"Verdict: {report['verdict']}")
    for v in report["failed_checks"]:
        print(f"  FAIL: {v}")
    for w in report["warnings"]:
        print(f"  WARN: {w}")
    print(f"Report: {artifacts['markdown']}")
    return EXIT_FAIL if report["verdict"] == "FAIL" else EXIT_PASS


def _check_app(args: argparse.Namespace, profile: dict) -> int:
    from aipreflight.appcheck import run_app_checks

    run_dir = _run_dir(profile, args.out)
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        results = run_app_checks(profile)
    except MissingDependency as e:
        _err(str(e))
        return EXIT_CONFIG
    except RuntimeError as e:
        _err(str(e))
        return EXIT_PROBE

    artifacts = {
        "json": str(run_dir / "aipreflight-report.json"),
        "markdown": str(run_dir / "aipreflight-report.md"),
    }
    report = report_mod.build_app_report(results, profile, artifacts)
    report_mod.write_reports(report, run_dir)
    _update_latest(run_dir)
    return _emit(report, artifacts)


def _check_inference(args: argparse.Namespace, profile: dict) -> int:
    if args.config:
        profile["probe"]["config"] = args.config
    if args.duration:
        profile["probe"]["duration"] = args.duration
    if args.interval:
        profile["probe"]["interval"] = args.interval

    run_dir = _run_dir(profile, args.out)
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.probes:
        probes_path = args.probes
        try:
            probes = load_probes(probes_path)
        except FileNotFoundError:
            _err(f"probe file not found: {probes_path}")
            return EXIT_CONFIG
    else:
        probes_path = str(run_dir / "llmprobe.jsonl")
        print(f"Running {profile['probe']['tool']} against {profile['probe']['config']} ...")
        try:
            run_llmprobe(
                profile["probe"]["config"],
                profile["probe"]["duration"],
                profile["probe"]["interval"],
                Path(probes_path),
            )
        except MissingDependency as e:
            _err(str(e))
            return EXIT_CONFIG
        except ProbeError as e:
            _err(str(e))
            return EXIT_PROBE
        probes = load_probes(probes_path)

    artifacts = {
        "probes": probes_path,
        "json": str(run_dir / "aipreflight-report.json"),
        "markdown": str(run_dir / "aipreflight-report.md"),
    }
    report = report_mod.build_report(probes, profile, probes_path, artifacts)
    report_mod.write_reports(report, run_dir)
    _update_latest(run_dir)
    return _emit(report, artifacts)


def _resolve_jsonl(path: str) -> str:
    p = Path(path)
    if p.is_dir():
        return str(p / "llmprobe.jsonl")
    return path


def cmd_report(args: argparse.Namespace) -> int:
    p = Path(args.run)
    json_path = p / "aipreflight-report.json" if p.is_dir() else p
    if not json_path.exists():
        _err(f"no report found at {json_path}")
        return EXIT_CONFIG
    import json

    report = json.loads(json_path.read_text())
    print(report_mod.render_markdown(report))
    return EXIT_PASS


def cmd_diagnose(args: argparse.Namespace) -> int:
    jsonl = _resolve_jsonl(args.run)
    try:
        probes = load_probes(jsonl)
    except FileNotFoundError:
        _err(f"probe file not found: {jsonl}")
        return EXIT_CONFIG

    server_metrics = None
    if args.prometheus:
        queries = load_queries(args.queries)
        server_metrics = collect_server_metrics(args.prometheus, probes, queries)
    elif args.prometheus_data:
        server_metrics = load_metrics_file(args.prometheus_data)

    print(diagnose(probes, server_metrics))
    return EXIT_PASS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aipreflight",
        description="Production readiness gate for AI applications and LLM inference endpoints.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="Run a readiness check against a profile.")
    c.add_argument("--profile", required=True, help="Path to a profile YAML file.")
    c.add_argument("--probes", help="Score an existing llmprobe JSONL file instead of probing live.")
    c.add_argument("--out", help="Output run directory (default: <outdir>/<profile>-<timestamp>).")
    c.add_argument("--config", help="Override the profile's probe config path.")
    c.add_argument("--duration", help="Override the profile's probe duration.")
    c.add_argument("--interval", help="Override the profile's probe interval.")
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("report", help="Re-render the Markdown report for a run.")
    r.add_argument("run", help="Run directory or aipreflight-report.json path.")
    r.set_defaults(func=cmd_report)

    d = sub.add_parser("diagnose", help="Correlate probe data with server metrics.")
    d.add_argument("run", help="Run directory or llmprobe JSONL path.")
    d.add_argument("--prometheus", help="Prometheus endpoint URL for live queries.")
    d.add_argument("--prometheus-data", help="Pre-collected Prometheus metrics JSON file.")
    d.add_argument("--queries", default="configs/prometheus/queries.yml", help="Prometheus queries file.")
    d.set_defaults(func=cmd_diagnose)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
