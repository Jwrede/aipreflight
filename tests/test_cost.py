"""Tests for the tokentoll cost adapter (no subprocess; synthetic scan dicts)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from aipreflight import cost
from aipreflight.checks import FAIL, PASS, WARN
from aipreflight.errors import MissingDependency


def scan(monthly, per_call, warnings=None, calls=1):
    return {
        "calls": [{"estimated_cost_per_call": per_call} for _ in range(calls)],
        "total_monthly_estimate": monthly,
        "assumptions": ["50000 calls/month per call site"],
        "warnings": warnings or [],
    }


BUDGET = {"max_cost_per_request_usd": 0.02, "max_monthly_cost_usd": 1000}


class TestEvaluateCost:
    def test_within_budget_passes(self):
        r = cost.evaluate_cost(scan(8.0, 0.0001), BUDGET)
        assert r.status == PASS
        assert "within budget" in r.summary

    def test_per_request_over_budget_fails(self):
        r = cost.evaluate_cost(scan(8.0, 0.05), BUDGET)
        assert r.status == FAIL
        assert "per-request" in r.summary

    def test_monthly_over_budget_fails(self):
        r = cost.evaluate_cost(scan(5000.0, 0.0001), BUDGET)
        assert r.status == FAIL
        assert "monthly" in r.summary

    def test_no_call_sites_warns(self):
        r = cost.evaluate_cost(scan(0.0, 0.0, calls=0), BUDGET)
        assert r.status == WARN

    def test_stale_pricing_note_does_not_change_verdict(self):
        r = cost.evaluate_cost(scan(8.0, 0.0001, warnings=["Pricing data is 23 days old."]), BUDGET)
        assert r.status == PASS
        assert "note:" in r.summary

    def test_details_are_explainable(self):
        r = cost.evaluate_cost(scan(8.0, 0.0001), BUDGET)
        assert r.details["total_monthly_estimate_usd"] == 8.0
        assert r.details["budget"]["max_monthly_cost_usd"] == 1000


class TestRunTokentoll:
    def test_missing_tokentoll_raises(self, monkeypatch):
        monkeypatch.setattr(cost.shutil, "which", lambda _: None)
        with pytest.raises(MissingDependency, match="tokentoll not found"):
            cost.run_tokentoll(["some/path"], 1000)
