"""Tests for the eval quality gate adapter."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from aipreflight import appcheck, evals
from aipreflight.checks import FAIL, PASS, SKIP, WARN

FIXTURES = Path(__file__).parent.parent / "fixtures" / "evals"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class TestEvaluate:
    def test_pass_rate_gate_passes(self):
        r = evals.evaluate_evals(_load("passing.json"), {"min_pass_rate": 0.9})
        assert r.status == PASS
        assert r.details["pass_rate"] == 0.95

    def test_pass_rate_gate_fails(self):
        r = evals.evaluate_evals(_load("failing.json"), {"min_pass_rate": 0.9})
        assert r.status == FAIL
        assert "below minimum" in r.summary

    def test_pass_rate_computed_from_counts(self):
        r = evals.evaluate_evals({"total": 10, "passed": 8}, {"min_pass_rate": 0.75})
        assert r.status == PASS
        assert r.details["pass_rate"] == 0.8

    def test_metric_min_gate_fails(self):
        cfg = {"metrics": {"retrieval_precision": {"min": 0.8}}}
        r = evals.evaluate_evals(_load("failing.json"), cfg)
        assert r.status == FAIL
        assert "retrieval_precision" in r.summary

    def test_metric_max_gate_fails(self):
        cfg = {"metrics": {"hallucination_rate": {"max": 0.05}}}
        r = evals.evaluate_evals(_load("failing.json"), cfg)
        assert r.status == FAIL
        assert "above maximum" in r.summary

    def test_metric_gates_pass(self):
        cfg = {
            "min_pass_rate": 0.9,
            "metrics": {
                "retrieval_precision": {"min": 0.8},
                "hallucination_rate": {"max": 0.05},
            },
        }
        assert evals.evaluate_evals(_load("passing.json"), cfg).status == PASS

    def test_missing_metric_is_violation(self):
        cfg = {"metrics": {"not_reported": {"min": 0.5}}}
        r = evals.evaluate_evals(_load("passing.json"), cfg)
        assert r.status == FAIL
        assert "not reported" in r.summary

    def test_nothing_to_gate_warns(self):
        r = evals.evaluate_evals({"foo": "bar"}, {})
        assert r.status == WARN


class TestRunEvals:
    def test_reads_results_file(self):
        cfg = {"results_file": str(FIXTURES / "passing.json"), "min_pass_rate": 0.9}
        assert evals.check_eval_gate(cfg).status == PASS

    def test_malformed_file_raises(self):
        cfg = {"results_file": str(FIXTURES / "malformed.json"), "min_pass_rate": 0.9}
        with pytest.raises(RuntimeError, match="could not parse"):
            evals.run_evals(cfg)

    def test_missing_file_raises(self):
        with pytest.raises(RuntimeError, match="not found"):
            evals.run_evals({"results_file": "/nope/results.json"})

    def test_command_stdout_json(self):
        cfg = {"command": "echo '{\"total\": 4, \"passed\": 4}'", "min_pass_rate": 1.0}
        assert evals.check_eval_gate(cfg).status == PASS

    def test_command_nonzero_no_json_raises(self):
        with pytest.raises(RuntimeError, match="emitted no"):
            evals.run_evals({"command": "exit 1"})

    def test_command_then_results_file(self, tmp_path):
        out = tmp_path / "r.json"
        cfg = {
            "command": f"echo '{{\"total\": 2, \"passed\": 2}}' > {out}",
            "results_file": str(out),
            "min_pass_rate": 1.0,
        }
        assert evals.check_eval_gate(cfg).status == PASS


class TestCheckEvalsRouting:
    def test_config_presence_mode_unchanged(self, tmp_path):
        # No gate keys -> legacy config-presence behavior.
        assert appcheck.check_evals({"command": "pytest", "path": str(tmp_path)}).status == PASS

    def test_gate_mode_triggers_on_results_file(self):
        cfg = {"results_file": str(FIXTURES / "failing.json"), "min_pass_rate": 0.9}
        assert appcheck.check_evals(cfg).status == FAIL

    def test_gate_mode_without_command_or_file_fails(self):
        assert appcheck.check_evals({"min_pass_rate": 0.9}).status == FAIL

    def test_absent_evals_skips(self):
        assert appcheck.check_evals(None).status == SKIP
