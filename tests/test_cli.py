"""Tests for the aipreflight CLI: exit codes and report artifacts."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from aipreflight import EXIT_CONFIG, EXIT_FAIL, EXIT_PASS
from aipreflight.cli import main

REPO = Path(__file__).parent.parent
PROFILE = str(REPO / "profiles" / "inference.yml")


def healthy(ttft_ms=200, latency_ms=3000, tps=5.0, status="healthy"):
    return {
        "provider": "test", "model": "m", "status": status,
        "ttft_ms": ttft_ms, "latency_ms": latency_ms, "tokens_per_sec": tps,
        "timestamp": "2026-01-01T00:00:00Z",
    }


def write_jsonl(probes, path: Path) -> str:
    path.write_text("".join(json.dumps(p) + "\n" for p in probes))
    return str(path)


def run_check(tmp_path, probes):
    jsonl = write_jsonl(probes, tmp_path / "probes.jsonl")
    out = tmp_path / "run"
    code = main(["check", "--profile", PROFILE, "--probes", jsonl, "--out", str(out)])
    return code, out


class TestCheckExitCodes:
    def test_pass(self, tmp_path):
        code, out = run_check(tmp_path, [healthy() for _ in range(10)])
        assert code == EXIT_PASS
        report = json.loads((out / "aipreflight-report.json").read_text())
        assert report["verdict"] == "PASS"

    def test_fail(self, tmp_path):
        code, out = run_check(tmp_path, [healthy(ttft_ms=900) for _ in range(10)])
        assert code == EXIT_FAIL
        report = json.loads((out / "aipreflight-report.json").read_text())
        assert report["verdict"] == "FAIL"
        assert any("TTFT" in c for c in report["failed_checks"])

    def test_warn_when_degraded_within_gate(self, tmp_path):
        probes = [healthy() for _ in range(19)] + [healthy(status="degraded")]
        code, out = run_check(tmp_path, probes)
        assert code == EXIT_PASS
        report = json.loads((out / "aipreflight-report.json").read_text())
        assert report["verdict"] == "WARN"
        assert report["warnings"]

    def test_missing_probe_file(self, tmp_path):
        code = main(["check", "--profile", PROFILE, "--probes", str(tmp_path / "nope.jsonl")])
        assert code == EXIT_CONFIG

    def test_invalid_profile(self, tmp_path):
        bad = tmp_path / "bad.yml"
        bad.write_text("name: bad\n")
        jsonl = write_jsonl([healthy()], tmp_path / "p.jsonl")
        code = main(["check", "--profile", str(bad), "--probes", jsonl])
        assert code == EXIT_CONFIG


class TestArtifacts:
    def test_writes_json_and_markdown(self, tmp_path):
        _, out = run_check(tmp_path, [healthy() for _ in range(10)])
        assert (out / "aipreflight-report.json").exists()
        md = (out / "aipreflight-report.md").read_text()
        assert md.startswith("# aipreflight: PASS")

    def test_report_subcommand_renders(self, tmp_path, capsys):
        _, out = run_check(tmp_path, [healthy() for _ in range(10)])
        code = main(["report", str(out)])
        assert code == EXIT_PASS
        assert "aipreflight: PASS" in capsys.readouterr().out
