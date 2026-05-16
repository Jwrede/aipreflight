"""Tests for scripts/compare.py sweep comparison logic."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from compare import analyze_run, percentile


def write_probes(path: Path, probes: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for p in probes:
            f.write(json.dumps(p) + "\n")


def make_probe(ttft_ms=200, latency_ms=3000, tps=5.0, status="healthy"):
    p = {
        "provider": "test",
        "model": "test-model",
        "status": status,
        "ttft_ms": ttft_ms,
        "latency_ms": latency_ms,
        "tokens_per_sec": tps,
        "timestamp": "2026-01-01T00:00:00Z",
    }
    if status == "error":
        del p["ttft_ms"]
        del p["latency_ms"]
        del p["tokens_per_sec"]
        p["error"] = "timeout"
    return p


class TestAnalyzeRun:
    def test_basic_metrics(self, tmp_path):
        probes = [make_probe(ttft_ms=100 + i * 10) for i in range(10)]
        path = tmp_path / "c1" / "llmprobe.jsonl"
        write_probes(path, probes)
        result = analyze_run(path)
        assert result["total"] == 10
        assert result["errors"] == 0
        assert result["error_rate"] == 0.0
        assert result["ttft_p50"] > 0
        assert result["ttft_p95"] > result["ttft_p50"]

    def test_with_errors(self, tmp_path):
        probes = [make_probe() for _ in range(8)]
        probes += [make_probe(status="error") for _ in range(2)]
        path = tmp_path / "c4" / "llmprobe.jsonl"
        write_probes(path, probes)
        result = analyze_run(path)
        assert result["total"] == 10
        assert result["errors"] == 2
        assert result["error_rate"] == 0.2

    def test_empty_file(self, tmp_path):
        path = tmp_path / "c1" / "llmprobe.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text("")
        result = analyze_run(path)
        assert result["total"] == 0

    def test_ordering(self, tmp_path):
        probes = [make_probe(ttft_ms=v) for v in [500, 100, 300, 200, 400]]
        path = tmp_path / "c2" / "llmprobe.jsonl"
        write_probes(path, probes)
        result = analyze_run(path)
        assert result["ttft_p50"] == 300
        assert result["throughput_min"] == 5.0


class TestPercentileCompare:
    def test_empty(self):
        assert percentile([], 95) == 0.0

    def test_sorted(self):
        assert percentile([1, 2, 3, 4, 5], 50) == 3
