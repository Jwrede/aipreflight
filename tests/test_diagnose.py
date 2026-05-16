"""Tests for scripts/diagnose.py with synthetic Prometheus data."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from diagnose import diagnose, load_probes, percentile


def make_probe(ttft_ms=200, latency_ms=3000, status="healthy", ts="2026-01-01T00:00:00Z"):
    p = {
        "provider": "test",
        "model": "test-model",
        "status": status,
        "timestamp": ts,
    }
    if status != "error":
        p["ttft_ms"] = ttft_ms
        p["latency_ms"] = latency_ms
        p["tokens_per_sec"] = 5.0
    else:
        p["error"] = "connection refused"
    return p


class TestDiagnoseClientOnly:
    def test_healthy_no_server_metrics(self):
        probes = [make_probe() for _ in range(10)]
        report = diagnose(probes, server_metrics=None)
        assert "Client-Side Observations" in report
        assert "Not available" in report
        assert "No issues detected" in report

    def test_errors_produce_causes(self):
        probes = [make_probe()] * 5 + [make_probe(status="error")] * 3
        report = diagnose(probes, server_metrics=None)
        assert "connection refused" in report.lower() or "Connection failure" in report

    def test_degraded_produces_recommendations(self):
        probes = [make_probe(status="degraded", ttft_ms=5000) for _ in range(10)]
        report = diagnose(probes, server_metrics=None)
        assert "sweep" in report.lower() or "concurrency" in report.lower()


class TestDiagnoseWithServerMetrics:
    def test_network_overhead_detected(self):
        probes = [make_probe(ttft_ms=800) for _ in range(10)]
        server_metrics = {
            "ttft": {"mean": 0.2, "max": 0.3, "unit": "seconds", "description": "Server TTFT p95"},
            "queue_depth": {"mean": 0, "max": 0, "unit": "count", "description": "Queue"},
            "kv_cache_usage": {"mean": 0.1, "max": 0.2, "unit": "percent", "description": "KV"},
        }
        report = diagnose(probes, server_metrics=server_metrics)
        assert "Network/proxy overhead detected" in report or "network overhead" in report.lower()

    def test_no_network_overhead(self):
        probes = [make_probe(ttft_ms=250) for _ in range(10)]
        server_metrics = {
            "ttft": {"mean": 0.22, "max": 0.25, "unit": "seconds", "description": "Server TTFT p95"},
            "queue_depth": {"mean": 0, "max": 0, "unit": "count", "description": "Queue"},
            "kv_cache_usage": {"mean": 0.1, "max": 0.2, "unit": "percent", "description": "KV"},
        }
        report = diagnose(probes, server_metrics=server_metrics)
        assert "align" in report.lower()

    def test_queue_pressure_flagged(self):
        probes = [make_probe(ttft_ms=500) for _ in range(10)]
        server_metrics = {
            "ttft": {"mean": 0.45, "max": 0.5, "unit": "seconds", "description": "Server TTFT p95"},
            "queue_depth": {"mean": 8, "max": 12, "unit": "count", "description": "Queue"},
            "kv_cache_usage": {"mean": 0.1, "max": 0.2, "unit": "percent", "description": "KV"},
        }
        report = diagnose(probes, server_metrics=server_metrics)
        assert "Queue pressure" in report

    def test_kv_cache_pressure_flagged(self):
        probes = [make_probe(ttft_ms=500) for _ in range(10)]
        server_metrics = {
            "ttft": {"mean": 0.45, "max": 0.5, "unit": "seconds", "description": "Server TTFT p95"},
            "queue_depth": {"mean": 0, "max": 1, "unit": "count", "description": "Queue"},
            "kv_cache_usage": {"mean": 0.7, "max": 0.9, "unit": "percent", "description": "KV"},
        }
        report = diagnose(probes, server_metrics=server_metrics)
        assert "KV cache pressure" in report


class TestPercentileDiagnose:
    def test_empty(self):
        assert percentile([], 50) == 0.0

    def test_values(self):
        assert percentile([100, 200, 300], 50) == 200
