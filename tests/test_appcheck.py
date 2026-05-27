"""Tests for app readiness checks (cost excluded; covered in test_cost)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from aipreflight import appcheck
from aipreflight.checks import FAIL, PASS, SKIP, WARN, aggregate_verdict


class TestEvals:
    def test_skip_when_absent(self):
        assert appcheck.check_evals(None).status == SKIP

    def test_fail_without_command(self):
        assert appcheck.check_evals({"path": "x"}).status == FAIL

    def test_fail_when_path_missing(self):
        assert appcheck.check_evals({"command": "pytest", "path": "/nope"}).status == FAIL

    def test_pass_when_configured(self, tmp_path):
        assert appcheck.check_evals({"command": "pytest", "path": str(tmp_path)}).status == PASS


class TestObservability:
    def test_fail_when_config_missing(self):
        assert appcheck.check_observability({"config": "/nope.yml"}).status == FAIL

    def test_warn_when_fields_missing(self, tmp_path):
        cfg = tmp_path / "o.yml"
        cfg.write_text("fields: [request_id, model]\n")
        r = appcheck.check_observability({"config": str(cfg), "required_fields": ["request_id", "model", "cost_usd"]})
        assert r.status == WARN
        assert "cost_usd" in r.summary

    def test_pass_with_all_fields(self, tmp_path):
        cfg = tmp_path / "o.yml"
        cfg.write_text("fields: [request_id, model]\n")
        r = appcheck.check_observability({"config": str(cfg), "required_fields": ["request_id", "model"]})
        assert r.status == PASS


class TestDeployment:
    def test_warn_without_runbook(self):
        assert appcheck.check_deployment({"gate_configured": True}).status == WARN

    def test_fail_when_runbook_missing(self):
        assert appcheck.check_deployment({"rollback_runbook": "/nope.md"}).status == FAIL

    def test_pass_when_runbook_present(self, tmp_path):
        rb = tmp_path / "rb.md"
        rb.write_text("# rollback\n")
        assert appcheck.check_deployment({"rollback_runbook": str(rb)}).status == PASS


class TestRunAppChecks:
    def test_cost_skipped_when_absent(self, tmp_path):
        rb = tmp_path / "rb.md"
        rb.write_text("# rollback\n")
        profile = {"deployment": {"rollback_runbook": str(rb)}}
        results = appcheck.run_app_checks(profile)
        names = {r.name: r.status for r in results}
        assert names["cost"] == SKIP
        assert names["deployment"] == PASS
        assert aggregate_verdict(results) == PASS
