"""Environment readiness checks for `aipreflight doctor`.

Read-only by default: it reports what is installed and what is missing without
changing anything, so a new user or a CI job can tell what setup is needed
before running `aipreflight check`. The opt-in --install path runs
scripts/install-deps.sh to fetch a prebuilt llmprobe binary.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import yaml

from aipreflight.checks import FAIL, PASS, SKIP, WARN, CheckResult

MIN_LLMPROBE = (1, 4, 0)
MIN_PYTHON = (3, 10)
DEFAULT_PROFILES = ["profiles/inference.yml", "profiles/app.yml", "profiles/rag.yml"]


def _ver_str(v: tuple[int, ...]) -> str:
    return ".".join(str(p) for p in v)


def _parse_semver(text: str) -> tuple[int, int, int] | None:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def check_python() -> CheckResult:
    v = sys.version_info
    ver = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= MIN_PYTHON:
        return CheckResult("python", PASS, f"Python {ver} (>= {_ver_str(MIN_PYTHON)})")
    return CheckResult("python", FAIL, f"Python {ver} below required {_ver_str(MIN_PYTHON)}")


def _llmprobe_version() -> str | None:
    try:
        out = subprocess.run(
            ["llmprobe", "version"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return (out.stdout + out.stderr).strip()


def check_llmprobe() -> CheckResult:
    minstr = _ver_str(MIN_LLMPROBE)
    if shutil.which("llmprobe") is None:
        return CheckResult(
            "llmprobe", WARN,
            "not found on PATH. Needed for the inference profile. Install with "
            "`./scripts/install-deps.sh` (or `aipreflight doctor --install`), or "
            "`go install github.com/Jwrede/llmprobe@latest`. The app and rag "
            "profiles do not need it.",
        )
    ver = _parse_semver(_llmprobe_version() or "")
    if ver is None:
        return CheckResult("llmprobe", WARN, f"installed but version could not be determined (need >= {minstr})")
    if ver < MIN_LLMPROBE:
        return CheckResult(
            "llmprobe", WARN,
            f"v{_ver_str(ver)} installed but >= {minstr} recommended; "
            "upgrade with ./scripts/install-deps.sh",
        )
    return CheckResult("llmprobe", PASS, f"v{_ver_str(ver)} (>= {minstr})")


def check_tokentoll() -> CheckResult:
    if shutil.which("tokentoll") is None:
        return CheckResult(
            "tokentoll", WARN,
            "not found. Needed only for the app profile cost gate. "
            "Install with `pip install tokentoll`.",
        )
    return CheckResult("tokentoll", PASS, "installed (app profile cost gate available)")


def check_profiles(paths: list[str]) -> CheckResult:
    bad, checked = [], 0
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        checked += 1
        try:
            yaml.safe_load(path.read_text())
        except yaml.YAMLError as e:
            bad.append(f"{p}: {e}")
    if bad:
        return CheckResult("profiles", FAIL, "profiles failed to parse: " + "; ".join(bad))
    if checked == 0:
        return CheckResult("profiles", SKIP, "no profiles found to check")
    return CheckResult("profiles", PASS, f"{checked} profile(s) parse cleanly")


def check_prometheus(url: str) -> CheckResult:
    health = url.rstrip("/") + "/-/healthy"
    try:
        with urlopen(health, timeout=5) as resp:  # noqa: S310 - operator-supplied URL
            code = resp.getcode()
    except (URLError, OSError) as e:
        return CheckResult("prometheus", WARN, f"not reachable at {url}: {e}")
    if code == 200:
        return CheckResult("prometheus", PASS, f"reachable at {url}")
    return CheckResult("prometheus", WARN, f"{url} returned HTTP {code}")


def run_doctor(profiles: list[str] | None = None, prometheus: str | None = None) -> list[CheckResult]:
    results = [
        check_python(),
        check_llmprobe(),
        check_tokentoll(),
        check_profiles(profiles or DEFAULT_PROFILES),
    ]
    if prometheus:
        results.append(check_prometheus(prometheus))
    return results


def install_deps(source: bool = False) -> int:
    script = Path(__file__).resolve().parent.parent / "scripts" / "install-deps.sh"
    if not script.exists():
        script = Path("scripts/install-deps.sh")
    if not script.exists():
        print(
            "aipreflight: scripts/install-deps.sh not found; "
            "run --install from a checkout of the repo.",
            file=sys.stderr,
        )
        return 2
    cmd = ["bash", str(script)] + (["--source"] if source else [])
    return subprocess.call(cmd)
