"""Load and validate aipreflight profiles.

A profile bundles everything needed for one readiness check: how to probe the
target, the SLA thresholds to gate on, and optional observability settings.
Invalid profiles raise ProfileError, which the CLI maps to exit code 2.
"""

from pathlib import Path

import yaml


class ProfileError(Exception):
    """Raised when a profile is missing, malformed, or fails validation."""


def load_profile(path: str) -> dict:
    """Load a profile YAML file, apply defaults, and validate it.

    Returns a normalized profile dict. Raises ProfileError on any problem.
    """
    p = Path(path)
    if not p.exists():
        raise ProfileError(f"Profile not found: {path}")

    try:
        with open(p) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ProfileError(f"Profile {path} is not valid YAML: {e}")

    if not isinstance(raw, dict):
        raise ProfileError(f"Profile {path} must be a YAML mapping at the top level.")

    return _validate(raw, path)


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ProfileError(msg)


VALID_KINDS = ("inference", "app", "rag")


def _is_eval_gate(cfg: dict) -> bool:
    return any(cfg.get(k) is not None for k in ("min_pass_rate", "metrics"))


def _validate(raw: dict, path: str) -> dict:
    _require(
        isinstance(raw.get("name"), str) and raw["name"].strip(),
        f"Profile {path}: missing required field 'name' (a short profile name).",
    )
    kind = raw.get("kind", "inference")
    _require(
        kind in VALID_KINDS,
        f"Profile {path}: 'kind' must be one of {VALID_KINDS}, got '{kind}'.",
    )

    report = raw.get("report") or {}
    _require(
        isinstance(report, dict),
        f"Profile {path}: 'report' must be a mapping if present.",
    )
    common = {
        "name": raw["name"],
        "kind": kind,
        "description": raw.get("description", ""),
        "report": {"outdir": report.get("outdir", "runs")},
    }

    if kind == "inference":
        return {**common, **_validate_inference(raw, path)}
    return {**common, **_validate_app(raw, path, kind)}


def _validate_inference(raw: dict, path: str) -> dict:
    probe = raw.get("probe")
    _require(isinstance(probe, dict), f"Profile {path}: missing required 'probe' section.")
    _require(
        isinstance(probe.get("config"), str) and probe["config"].strip(),
        f"Profile {path}: 'probe.config' is required (path to the llmprobe config).",
    )

    thresholds = raw.get("thresholds")
    _require(isinstance(thresholds, dict), f"Profile {path}: missing required 'thresholds' section.")
    sla = thresholds.get("sla")
    _require(
        isinstance(sla, dict) and sla,
        f"Profile {path}: 'thresholds.sla' is required and must define at least one limit.",
    )

    observability = raw.get("observability") or {}
    _require(isinstance(observability, dict), f"Profile {path}: 'observability' must be a mapping if present.")

    return {
        "probe": {
            "tool": probe.get("tool", "llmprobe"),
            "config": probe["config"],
            "duration": str(probe.get("duration", "30s")),
            "interval": str(probe.get("interval", "5s")),
        },
        "thresholds": {"sla": sla, "gate": thresholds.get("gate", {})},
        "observability": {
            "prometheus": observability.get("prometheus"),
            "queries": observability.get("queries", "configs/prometheus/queries.yml"),
        },
    }


def _validate_app(raw: dict, path: str, kind: str = "app") -> dict:
    sections = ("cost", "evals", "observability", "deployment")
    present = {s: raw.get(s) for s in sections if raw.get(s) is not None}
    _require(
        present,
        f"Profile {path}: an {kind} profile must define at least one of {sections}.",
    )
    for name, value in present.items():
        _require(isinstance(value, dict), f"Profile {path}: '{name}' must be a mapping.")

    if kind == "rag":
        evals = present.get("evals")
        _require(
            isinstance(evals, dict),
            f"Profile {path}: a rag profile must define an 'evals' section "
            "(RAG readiness is a quality gate, not just infrastructure).",
        )
        _require(
            _is_eval_gate(evals),
            f"Profile {path}: a rag 'evals' section must gate on results "
            "(set 'min_pass_rate' and/or 'metrics').",
        )

    cost = present.get("cost")
    if cost is not None:
        _require(
            isinstance(cost.get("scan_paths"), list) and cost["scan_paths"],
            f"Profile {path}: 'cost.scan_paths' is required and must be a non-empty list.",
        )

    return {
        "cost": cost,
        "evals": present.get("evals"),
        "observability": present.get("observability"),
        "deployment": present.get("deployment"),
    }
