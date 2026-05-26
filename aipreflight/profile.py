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


def _validate(raw: dict, path: str) -> dict:
    _require(
        isinstance(raw.get("name"), str) and raw["name"].strip(),
        f"Profile {path}: missing required field 'name' (a short profile name).",
    )

    probe = raw.get("probe")
    _require(
        isinstance(probe, dict),
        f"Profile {path}: missing required 'probe' section.",
    )
    _require(
        isinstance(probe.get("config"), str) and probe["config"].strip(),
        f"Profile {path}: 'probe.config' is required (path to the llmprobe config).",
    )

    thresholds = raw.get("thresholds")
    _require(
        isinstance(thresholds, dict),
        f"Profile {path}: missing required 'thresholds' section.",
    )
    sla = thresholds.get("sla")
    _require(
        isinstance(sla, dict) and sla,
        f"Profile {path}: 'thresholds.sla' is required and must define at least one limit.",
    )

    observability = raw.get("observability") or {}
    _require(
        isinstance(observability, dict),
        f"Profile {path}: 'observability' must be a mapping if present.",
    )
    report = raw.get("report") or {}
    _require(
        isinstance(report, dict),
        f"Profile {path}: 'report' must be a mapping if present.",
    )

    return {
        "name": raw["name"],
        "description": raw.get("description", ""),
        "probe": {
            "tool": probe.get("tool", "llmprobe"),
            "config": probe["config"],
            "duration": str(probe.get("duration", "30s")),
            "interval": str(probe.get("interval", "5s")),
        },
        "thresholds": {
            "sla": sla,
            "gate": thresholds.get("gate", {}),
        },
        "observability": {
            "prometheus": observability.get("prometheus"),
            "queries": observability.get("queries", "configs/prometheus/queries.yml"),
        },
        "report": {
            "outdir": report.get("outdir", "runs"),
        },
    }
