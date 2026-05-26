"""Tests for scripts/report.py gate and verdict logic."""

import json
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from aipreflight.analyze import analyze, check_gate, load_probes, percentile, verdict_from_analysis


def write_jsonl(probes: list[dict], path: Path):
    with open(path, "w") as f:
        for p in probes:
            f.write(json.dumps(p) + "\n")


def make_healthy_probe(ttft_ms=200, latency_ms=3000, tps=5.0, ts="2026-01-01T00:00:00Z"):
    return {
        "provider": "test",
        "model": "test-model",
        "status": "healthy",
        "ttft_ms": ttft_ms,
        "latency_ms": latency_ms,
        "tokens_per_sec": tps,
        "timestamp": ts,
    }


def make_error_probe(error="timeout", ts="2026-01-01T00:00:00Z"):
    return {
        "provider": "test",
        "model": "test-model",
        "status": "error",
        "error": error,
        "timestamp": ts,
    }


def make_degraded_probe(ttft_ms=3000, latency_ms=10000, tps=1.5, ts="2026-01-01T00:00:00Z"):
    return {
        "provider": "test",
        "model": "test-model",
        "status": "degraded",
        "ttft_ms": ttft_ms,
        "latency_ms": latency_ms,
        "tokens_per_sec": tps,
        "timestamp": ts,
    }


THRESHOLDS = {
    "sla": {
        "ttft_ms": 500,
        "latency_ms": 10000,
        "min_throughput": 3.0,
        "max_error_rate": 0.01,
    },
    "gate": {
        "min_probes": 5,
        "pass_rate": 0.95,
    },
}


class TestPercentile:
    def test_empty_list(self):
        assert percentile([], 50) == 0.0

    def test_single_value(self):
        assert percentile([42.0], 95) == 42.0

    def test_p50(self):
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        assert percentile(values, 50) == 60

    def test_p95(self):
        values = list(range(1, 101))
        assert percentile(values, 95) == 96


class TestAnalyze:
    def test_all_healthy(self):
        probes = [make_healthy_probe() for _ in range(10)]
        result = analyze(probes)
        assert result["total"] == 10
        assert result["statuses"]["healthy"] == 10
        assert result["statuses"]["error"] == 0
        assert len(result["ttfts"]) == 10
        assert len(result["errors"]) == 0

    def test_mixed_statuses(self):
        probes = [
            make_healthy_probe(),
            make_healthy_probe(),
            make_degraded_probe(),
            make_error_probe(),
        ]
        result = analyze(probes)
        assert result["total"] == 4
        assert result["statuses"]["healthy"] == 2
        assert result["statuses"]["degraded"] == 1
        assert result["statuses"]["error"] == 1
        assert len(result["ttfts"]) == 3
        assert len(result["errors"]) == 1

    def test_empty_probes(self):
        result = analyze([])
        assert result["total"] == 0
        assert len(result["ttfts"]) == 0


class TestCheckGate:
    def test_pass_all_healthy(self):
        probes = [make_healthy_probe() for _ in range(10)]
        analysis = analyze(probes)
        passed, violations = check_gate(analysis, THRESHOLDS)
        assert passed is True
        assert violations == []

    def test_fail_insufficient_probes(self):
        probes = [make_healthy_probe() for _ in range(3)]
        analysis = analyze(probes)
        passed, violations = check_gate(analysis, THRESHOLDS)
        assert passed is False
        assert "Insufficient data" in violations[0]

    def test_fail_ttft_violation(self):
        probes = [make_healthy_probe(ttft_ms=600) for _ in range(10)]
        analysis = analyze(probes)
        passed, violations = check_gate(analysis, THRESHOLDS)
        assert passed is False
        assert any("TTFT" in v for v in violations)

    def test_fail_latency_violation(self):
        probes = [make_healthy_probe(latency_ms=12000) for _ in range(10)]
        analysis = analyze(probes)
        passed, violations = check_gate(analysis, THRESHOLDS)
        assert passed is False
        assert any("Latency" in v for v in violations)

    def test_fail_throughput_violation(self):
        probes = [make_healthy_probe(tps=1.5) for _ in range(10)]
        analysis = analyze(probes)
        passed, violations = check_gate(analysis, THRESHOLDS)
        assert passed is False
        assert any("Throughput" in v for v in violations)

    def test_fail_error_rate(self):
        probes = [make_healthy_probe() for _ in range(8)]
        probes += [make_error_probe() for _ in range(2)]
        analysis = analyze(probes)
        passed, violations = check_gate(analysis, THRESHOLDS)
        assert passed is False
        assert any("Error rate" in v for v in violations)

    def test_fail_pass_rate(self):
        probes = [make_healthy_probe() for _ in range(8)]
        probes += [make_degraded_probe() for _ in range(4)]
        analysis = analyze(probes)
        passed, violations = check_gate(analysis, THRESHOLDS)
        assert passed is False
        assert any("Pass rate" in v for v in violations)

    def test_pass_at_boundary(self):
        probes = [make_healthy_probe(ttft_ms=500) for _ in range(10)]
        analysis = analyze(probes)
        passed, _ = check_gate(analysis, THRESHOLDS)
        assert passed is True


class TestVerdictFromAnalysis:
    def test_ready_no_thresholds(self):
        probes = [make_healthy_probe() for _ in range(10)]
        analysis = analyze(probes)
        verdict, _ = verdict_from_analysis(analysis, None)
        assert verdict == "READY"

    def test_not_ready_high_errors(self):
        probes = [make_error_probe() for _ in range(10)]
        analysis = analyze(probes)
        verdict, _ = verdict_from_analysis(analysis, None)
        assert verdict == "NOT READY"

    def test_degraded(self):
        probes = [make_healthy_probe() for _ in range(7)]
        probes += [make_degraded_probe() for _ in range(3)]
        probes += [make_error_probe()]
        analysis = analyze(probes)
        verdict, _ = verdict_from_analysis(analysis, None)
        assert verdict == "DEGRADED"

    def test_ready_with_warnings(self):
        probes = [make_healthy_probe() for _ in range(9)]
        probes += [make_degraded_probe()]
        analysis = analyze(probes)
        verdict, _ = verdict_from_analysis(analysis, None)
        assert verdict == "READY WITH WARNINGS"

    def test_unknown_empty(self):
        analysis = analyze([])
        verdict, _ = verdict_from_analysis(analysis, None)
        assert verdict == "UNKNOWN"


class TestLoadProbes:
    def test_load_from_file(self, tmp_path):
        probes = [make_healthy_probe(), make_error_probe()]
        path = tmp_path / "test.jsonl"
        write_jsonl(probes, path)
        loaded = load_probes(str(path))
        assert len(loaded) == 2
        assert loaded[0]["status"] == "healthy"
        assert loaded[1]["status"] == "error"

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        loaded = load_probes(str(path))
        assert loaded == []

    def test_blank_lines_ignored(self, tmp_path):
        path = tmp_path / "blanks.jsonl"
        content = json.dumps(make_healthy_probe()) + "\n\n\n" + json.dumps(make_healthy_probe()) + "\n"
        path.write_text(content)
        loaded = load_probes(str(path))
        assert len(loaded) == 2
