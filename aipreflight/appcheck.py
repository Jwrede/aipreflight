"""Readiness checks for hosted-API AI and RAG applications (profile kind: app, rag).

These are checks that need no llmprobe or GPU: cost budget, eval quality,
observability fields, and a rollback path. Each returns a CheckResult; the CLI
aggregates them into one verdict.

The eval check has two modes. When the profile asks for a quality gate (it sets
min_pass_rate, metrics, or results_file) the eval command is run and scored by
aipreflight.evals. Otherwise this only verifies an eval suite is configured and
present, leaving execution to CI.
"""

from pathlib import Path

import yaml

from aipreflight.checks import FAIL, PASS, SKIP, WARN, CheckResult
from aipreflight.cost import check_cost
from aipreflight.evals import check_eval_gate


def _is_quality_gate(cfg: dict) -> bool:
    return any(cfg.get(k) is not None for k in ("min_pass_rate", "metrics", "results_file"))


def check_evals(cfg: dict | None) -> CheckResult:
    if not cfg:
        return CheckResult("evals", SKIP, "no eval suite configured")
    command = cfg.get("command")
    path = cfg.get("path")

    if _is_quality_gate(cfg):
        if not command and not cfg.get("results_file"):
            return CheckResult("evals", FAIL, "eval quality gate needs a 'command' or 'results_file'")
        return check_eval_gate(cfg)

    if not command:
        return CheckResult("evals", FAIL, "evals section present but no 'command' configured")
    if path and not Path(path).exists():
        return CheckResult("evals", FAIL, f"eval path not found: {path}", {"command": command})
    return CheckResult(
        "evals", PASS,
        f"eval suite configured: `{command}` (add min_pass_rate/metrics to gate on results)",
        {"command": command, "path": path},
    )


def check_observability(cfg: dict | None) -> CheckResult:
    if not cfg:
        return CheckResult("observability", SKIP, "no observability config")
    config_path = cfg.get("config")
    required = cfg.get("required_fields", [])
    if not config_path:
        return CheckResult("observability", FAIL, "observability section present but no 'config' path")
    p = Path(config_path)
    if not p.exists():
        return CheckResult("observability", FAIL, f"telemetry config not found: {config_path}")

    try:
        declared = yaml.safe_load(p.read_text()) or {}
    except yaml.YAMLError as e:
        return CheckResult("observability", FAIL, f"telemetry config is not valid YAML: {e}")
    declared_fields = set(declared.get("fields", []))
    missing = [f for f in required if f not in declared_fields]
    details = {"config": config_path, "required_fields": required, "declared_fields": sorted(declared_fields)}
    if missing:
        return CheckResult(
            "observability", WARN,
            f"telemetry config present but missing fields: {', '.join(missing)}",
            details,
        )
    return CheckResult(
        "observability", PASS,
        f"telemetry config present with all {len(required)} required fields",
        details,
    )


def check_deployment(cfg: dict | None) -> CheckResult:
    if not cfg:
        return CheckResult("deployment", SKIP, "no deployment config")
    runbook = cfg.get("rollback_runbook")
    if not runbook:
        return CheckResult("deployment", WARN, "no rollback_runbook configured")
    if not Path(runbook).exists():
        return CheckResult("deployment", FAIL, f"rollback runbook not found: {runbook}")
    return CheckResult("deployment", PASS, f"rollback runbook present: {runbook}", {"rollback_runbook": runbook})


def run_app_checks(profile: dict) -> list[CheckResult]:
    """Run all configured app checks. May raise MissingDependency (cost gate)."""
    results = []
    cost_cfg = profile.get("cost")
    if cost_cfg:
        results.append(check_cost(cost_cfg))
    else:
        results.append(CheckResult("cost", SKIP, "no cost budget configured"))
    results.append(check_evals(profile.get("evals")))
    results.append(check_observability(profile.get("observability")))
    results.append(check_deployment(profile.get("deployment")))
    return results
