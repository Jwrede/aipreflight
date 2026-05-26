"""Tests for profile loading and validation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from aipreflight.profile import ProfileError, load_profile

REPO = Path(__file__).parent.parent


def write_profile(tmp_path, text: str) -> str:
    p = tmp_path / "profile.yml"
    p.write_text(text)
    return str(p)


VALID = """
name: test
probe:
  config: configs/llmprobe/vllm.yml
thresholds:
  sla:
    ttft_ms: 500
"""


class TestValidProfile:
    def test_shipped_inference_profile_loads(self):
        prof = load_profile(str(REPO / "profiles" / "inference.yml"))
        assert prof["name"] == "inference"
        assert prof["thresholds"]["sla"]["ttft_ms"] == 500

    def test_defaults_applied(self, tmp_path):
        prof = load_profile(write_profile(tmp_path, VALID))
        assert prof["probe"]["tool"] == "llmprobe"
        assert prof["probe"]["duration"] == "30s"
        assert prof["probe"]["interval"] == "5s"
        assert prof["report"]["outdir"] == "runs"
        assert prof["observability"]["queries"].endswith("queries.yml")


class TestInvalidProfile:
    def test_missing_file(self):
        with pytest.raises(ProfileError, match="not found"):
            load_profile("/nonexistent/profile.yml")

    def test_missing_name(self, tmp_path):
        text = "probe:\n  config: c.yml\nthresholds:\n  sla:\n    ttft_ms: 500\n"
        with pytest.raises(ProfileError, match="name"):
            load_profile(write_profile(tmp_path, text))

    def test_missing_probe(self, tmp_path):
        text = "name: x\nthresholds:\n  sla:\n    ttft_ms: 500\n"
        with pytest.raises(ProfileError, match="probe"):
            load_profile(write_profile(tmp_path, text))

    def test_missing_probe_config(self, tmp_path):
        text = "name: x\nprobe: {}\nthresholds:\n  sla:\n    ttft_ms: 500\n"
        with pytest.raises(ProfileError, match="probe.config"):
            load_profile(write_profile(tmp_path, text))

    def test_missing_sla(self, tmp_path):
        text = "name: x\nprobe:\n  config: c.yml\nthresholds: {}\n"
        with pytest.raises(ProfileError, match="sla"):
            load_profile(write_profile(tmp_path, text))

    def test_not_a_mapping(self, tmp_path):
        with pytest.raises(ProfileError, match="mapping"):
            load_profile(write_profile(tmp_path, "- just\n- a\n- list\n"))
