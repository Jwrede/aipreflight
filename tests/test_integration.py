"""End-to-end readiness runs through the CLI, fully offline.

Exercises every adapter without paid APIs, GPUs, or network: probes from a JSONL
fixture (fake llmprobe), a monkeypatched tokentoll scan (fake cost), eval results
from a JSON fixture (fake eval output), and a Prometheus metrics file (fake server
metrics). The point is that a full PASS or FAIL verdict is reproducible in CI.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))
from aipreflight import EXIT_FAIL, EXIT_PASS
from aipreflight import cost
from aipreflight.cli import main

FIXTURES = REPO / "fixtures" / "evals"


@pytest.fixture
def fake_tokentoll(monkeypatch):
    """Make the cost gate return a within-budget scan with no real tokentoll."""

    def _scan(scan_paths, calls_per_month):
        return {
            "calls": [{"estimated_cost_per_call": 0.0002}],
            "total_monthly_estimate": 9.6,
            "assumptions": [f"{calls_per_month} calls/month"],
            "warnings": [],
        }

    monkeypatch.setattr(cost, "run_tokentoll", _scan)


def _full_app_profile(tmp_path, eval_results: str) -> str:
    obs = tmp_path / "obs.yml"
    obs.write_text("fields: [request_id, model, cost_usd]\n")
    rb = tmp_path / "rb.md"
    rb.write_text("# rollback\n")
    prof = tmp_path / "app.yml"
    prof.write_text(f"""
name: app
kind: app
cost:
  scan_paths: [examples/hosted-api-app]
  calls_per_month: 48000
  max_cost_per_request_usd: 0.02
  max_monthly_cost_usd: 1000
evals:
  results_file: {eval_results}
  min_pass_rate: 0.9
  metrics:
    retrieval_precision: {{min: 0.8}}
    hallucination_rate: {{max: 0.05}}
observability:
  config: {obs}
  required_fields: [request_id, model, cost_usd]
deployment:
  rollback_runbook: {rb}
""")
    return str(prof)


def _checks(out: Path) -> dict:
    report = json.loads((out / "aipreflight-report.json").read_text())
    return report, {c["name"]: c["status"] for c in report["checks"]}


class TestAppAllAdapters:
    def test_full_pass(self, tmp_path, fake_tokentoll):
        prof = _full_app_profile(tmp_path, str(FIXTURES / "passing.json"))
        out = tmp_path / "run"
        code = main(["check", "--profile", prof, "--out", str(out)])
        assert code == EXIT_PASS
        report, status = _checks(out)
        assert report["verdict"] == "PASS"
        assert status == {"cost": "PASS", "evals": "PASS", "observability": "PASS", "deployment": "PASS"}

    def test_fails_on_quality_while_infra_green(self, tmp_path, fake_tokentoll):
        prof = _full_app_profile(tmp_path, str(FIXTURES / "failing.json"))
        out = tmp_path / "run"
        code = main(["check", "--profile", prof, "--out", str(out)])
        assert code == EXIT_FAIL
        report, status = _checks(out)
        assert report["verdict"] == "FAIL"
        assert status["evals"] == "FAIL"
        # Infrastructure checks stay green: quality is the only thing blocking the ship.
        assert status["cost"] == "PASS"
        assert status["observability"] == "PASS"
        assert status["deployment"] == "PASS"


class TestRagEndToEnd:
    def test_pass(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIPREFLIGHT_RAG_BROKEN", raising=False)
        out = tmp_path / "run"
        code = main(["check", "--profile", str(REPO / "profiles" / "rag.yml"), "--out", str(out)])
        assert code == EXIT_PASS
        report, status = _checks(out)
        assert report["verdict"] == "PASS"
        assert status["evals"] == "PASS"

    def test_broken_retrieval_fails(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIPREFLIGHT_RAG_BROKEN", "1")
        out = tmp_path / "run"
        code = main(["check", "--profile", str(REPO / "profiles" / "rag.yml"), "--out", str(out)])
        assert code == EXIT_FAIL
        report, status = _checks(out)
        assert report["verdict"] == "FAIL"
        assert status["evals"] == "FAIL"
        assert status["observability"] == "PASS"


class TestDiagnoseWithFakePrometheus:
    def test_diagnose_reads_metrics_file(self, tmp_path, capsys):
        probes = tmp_path / "llmprobe.jsonl"
        probes.write_text("".join(
            json.dumps({
                "provider": "test", "model": "m", "status": "healthy",
                "ttft_ms": 800, "latency_ms": 3000, "tokens_per_sec": 5.0,
                "timestamp": "2026-01-01T00:00:00Z",
            }) + "\n" for _ in range(10)
        ))
        metrics = tmp_path / "prom.json"
        metrics.write_text(json.dumps({
            "ttft": {"mean": 0.2, "max": 0.3, "unit": "seconds", "description": "Server TTFT p95"},
            "queue_depth": {"mean": 0, "max": 0, "unit": "count", "description": "Queue"},
            "kv_cache_usage": {"mean": 0.1, "max": 0.2, "unit": "percent", "description": "KV"},
        }))
        code = main(["diagnose", str(probes), "--prometheus-data", str(metrics)])
        assert code == EXIT_PASS
        assert "network/proxy overhead" in capsys.readouterr().out.lower()
