"""Eval quality gate adapter.

aipreflight does not implement evals. It runs whatever eval command you already
have (pytest, promptfoo, ragas, a custom script) and turns its result into one
pass/fail gate. This is the layer between "the endpoint is up" and "the AI
feature is safe to ship".

Adapter contract
----------------
The eval step must produce JSON, either on stdout (the `command` mode) or in a
file (the `results_file` mode). aipreflight reads these fields:

    {
      "total": 10,            # number of cases run (optional if pass_rate given)
      "passed": 9,            # number of cases that passed (optional if pass_rate)
      "pass_rate": 0.9,       # overall pass rate; computed from passed/total if absent
      "metrics": {            # optional named metrics for richer gating (e.g. RAG)
        "retrieval_precision": 0.85,
        "answer_quality": 0.78,
        "hallucination_rate": 0.0
      }
    }

Any extra fields (e.g. a "cases" list) are ignored by the gate but preserved in
the report details. The eval command's own exit code does not decide the gate;
the reported numbers do. A non-zero exit only matters if it left no parseable
JSON behind.

Profile config (the `evals` section)
-------------------------------------
    evals:
      command: "python evals/run_evals.py"   # produces the JSON above
      results_file: evals/results.json       # optional: read this instead of stdout
      min_pass_rate: 0.9                      # gate on overall pass rate
      metrics:                                # optional per-metric gates
        retrieval_precision: {min: 0.8}
        hallucination_rate: {max: 0.05}

`command` and `results_file` may be combined: the command runs, then the file it
wrote is read. At least one of them must be present, and at least one of
`min_pass_rate` / `metrics` makes this a quality gate (otherwise the lighter
config-presence check in appcheck applies).
"""

import json
import subprocess
from pathlib import Path

from aipreflight.checks import FAIL, PASS, WARN, CheckResult


def run_evals(cfg: dict) -> dict:
    """Run the eval command and/or read its results file. Returns parsed JSON.

    Raises RuntimeError if the command fails with no parseable output, or if the
    JSON cannot be read or parsed.
    """
    command = cfg.get("command")
    results_file = cfg.get("results_file")

    proc = None
    if command:
        try:
            proc = subprocess.run(command, shell=True, capture_output=True, text=True)
        except OSError as e:
            raise RuntimeError(f"could not run eval command {command!r}: {e}")

    if results_file:
        p = Path(results_file)
        if not p.exists():
            detail = f" (command exited {proc.returncode}: {proc.stderr.strip()})" if proc else ""
            raise RuntimeError(f"eval results file not found: {results_file}{detail}")
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"could not parse eval results file {results_file}: {e}")

    if proc is None:
        raise RuntimeError("eval gate needs a 'command' or a 'results_file'")

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        if proc.returncode != 0:
            raise RuntimeError(
                f"eval command {command!r} exited {proc.returncode} and emitted no "
                f"JSON: {proc.stderr.strip()}"
            )
        raise RuntimeError(f"could not parse eval command output as JSON: {e}")


def _pass_rate(results: dict) -> float | None:
    if results.get("pass_rate") is not None:
        return float(results["pass_rate"])
    total = results.get("total")
    passed = results.get("passed")
    if total:
        return passed / total if passed is not None else None
    return None


def evaluate_evals(results: dict, cfg: dict) -> CheckResult:
    """Gate a parsed eval result against the thresholds in the profile."""
    violations: list[str] = []
    summary_bits: list[str] = []

    min_pass_rate = cfg.get("min_pass_rate")
    rate = _pass_rate(results)
    if min_pass_rate is not None:
        if rate is None:
            violations.append("min_pass_rate set but eval output reported no pass rate")
        else:
            summary_bits.append(f"pass rate {rate:.0%} (min {min_pass_rate:.0%})")
            if rate < min_pass_rate:
                violations.append(f"pass rate {rate:.0%} below minimum {min_pass_rate:.0%}")
    elif rate is not None:
        summary_bits.append(f"pass rate {rate:.0%}")

    reported = results.get("metrics", {}) or {}
    metric_gates = cfg.get("metrics", {}) or {}
    for name, bounds in metric_gates.items():
        if name not in reported:
            violations.append(f"metric '{name}' not reported by eval")
            continue
        value = reported[name]
        lo = bounds.get("min")
        hi = bounds.get("max")
        summary_bits.append(f"{name}={value:.2f}")
        if lo is not None and value < lo:
            violations.append(f"{name} {value:.2f} below minimum {lo:.2f}")
        if hi is not None and value > hi:
            violations.append(f"{name} {value:.2f} above maximum {hi:.2f}")

    details = {
        "pass_rate": rate,
        "min_pass_rate": min_pass_rate,
        "reported_metrics": reported,
        "metric_gates": metric_gates,
        "total": results.get("total"),
        "passed": results.get("passed"),
    }

    summary = ", ".join(summary_bits) if summary_bits else "eval completed"
    if violations:
        return CheckResult("evals", FAIL, "; ".join(violations), details)
    if rate is None and not metric_gates:
        return CheckResult(
            "evals", WARN,
            "eval ran but reported nothing to gate on (no pass rate or metrics)",
            details,
        )
    return CheckResult("evals", PASS, f"quality gate passed: {summary}", details)


def check_eval_gate(cfg: dict) -> CheckResult:
    """Run the eval command and gate its result. Raises RuntimeError on exec error."""
    results = run_evals(cfg)
    return evaluate_evals(results, cfg)
