"""Cost gate adapter built on tokentoll.

tokentoll statically scans source for LLM API call sites and estimates cost.
We run `tokentoll scan --format json`, then gate the result against the budget
configured in the profile. The CheckResult keeps the calculation explainable:
it carries the per-call and monthly estimates, the call volume assumption, and
which budget limit was exceeded.
"""

import json
import shutil
import subprocess

from aipreflight.checks import FAIL, PASS, WARN, CheckResult
from aipreflight.errors import MissingDependency


def run_tokentoll(scan_paths: list[str], calls_per_month: int) -> dict:
    """Run `tokentoll scan` and return its parsed JSON. Raises MissingDependency
    if tokentoll is not installed, RuntimeError if it fails or emits bad JSON."""
    if shutil.which("tokentoll") is None:
        raise MissingDependency(
            "tokentoll not found on PATH. Install it with `pip install tokentoll`, "
            "or remove the 'cost' section from the profile to skip the cost gate."
        )
    cmd = [
        "tokentoll", "scan",
        "--format", "json",
        "--calls-per-month", str(calls_per_month),
        *scan_paths,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"tokentoll exited with code {proc.returncode}: {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"could not parse tokentoll output: {e}")


def evaluate_cost(scan: dict, budget: dict) -> CheckResult:
    """Gate a tokentoll scan result against budget limits."""
    calls = scan.get("calls", [])
    monthly = scan.get("total_monthly_estimate", 0.0)
    per_call = max((c.get("estimated_cost_per_call", 0.0) for c in calls), default=0.0)

    max_per_call = budget.get("max_cost_per_request_usd")
    max_monthly = budget.get("max_monthly_cost_usd")

    violations = []
    if max_per_call is not None and per_call > max_per_call:
        violations.append(
            f"per-request cost ${per_call:.4f} exceeds budget ${max_per_call:.4f}"
        )
    if max_monthly is not None and monthly > max_monthly:
        violations.append(
            f"monthly cost ${monthly:,.2f} exceeds budget ${max_monthly:,.2f}"
        )

    details = {
        "call_sites": len(calls),
        "max_cost_per_request_usd": per_call,
        "total_monthly_estimate_usd": monthly,
        "assumptions": scan.get("assumptions", []),
        "tokentoll_warnings": scan.get("warnings", []),
        "budget": {"max_cost_per_request_usd": max_per_call, "max_monthly_cost_usd": max_monthly},
    }

    if violations:
        return CheckResult("cost", FAIL, "; ".join(violations), details)
    if not calls:
        return CheckResult(
            "cost", WARN,
            "no LLM call sites found to estimate cost", details,
        )
    # Within budget is a PASS. tokentoll's own notices (e.g. stale pricing) are
    # surfaced as a note in the summary, but do not change the verdict.
    summary = f"${monthly:,.2f}/mo across {len(calls)} call site(s), within budget"
    if scan.get("warnings"):
        summary += f" (note: {scan['warnings'][0]})"
    return CheckResult("cost", PASS, summary, details)


def check_cost(cost_cfg: dict) -> CheckResult:
    """Run the full cost gate from a profile's cost config."""
    scan = run_tokentoll(
        cost_cfg["scan_paths"],
        cost_cfg.get("calls_per_month", 1000),
    )
    return evaluate_cost(scan, cost_cfg)
