"""Probe data loading and llmprobe execution."""

import json
import shutil
import subprocess
from pathlib import Path


class ProbeError(Exception):
    """Raised when a probe run fails to execute or produce data."""


class MissingDependency(ProbeError):
    """Raised when a required external tool (e.g. llmprobe) is not installed."""


def load_probes(path: str) -> list[dict]:
    probes = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                probes.append(json.loads(line))
    return probes


def run_llmprobe(config: str, duration: str, interval: str, out_path: Path) -> Path:
    """Run `llmprobe watch` and write JSONL to out_path. Returns the path.

    Raises ProbeError if llmprobe is missing or exits non-zero.
    """
    if shutil.which("llmprobe") is None:
        raise MissingDependency(
            "llmprobe not found on PATH. Install it with "
            "`go install github.com/Jwrede/llmprobe@latest`, or pass --probes "
            "to score an existing JSONL file."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "llmprobe", "watch",
        "--interval", interval,
        "--duration", duration,
        "-f", "json",
        "-c", config,
    ]
    with open(out_path, "w") as out:
        proc = subprocess.run(cmd, stdout=out, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise ProbeError(
            f"llmprobe exited with code {proc.returncode}: {proc.stderr.strip()}"
        )
    return out_path
