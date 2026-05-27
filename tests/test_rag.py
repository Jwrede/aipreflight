"""Tests for the RAG profile and the offline RAG example pipeline."""

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples" / "rag-app"))

from aipreflight.profile import ProfileError, load_profile  # noqa: E402


@pytest.fixture
def rag(monkeypatch):
    monkeypatch.delenv("AIPREFLIGHT_RAG_BROKEN", raising=False)
    import rag as rag_mod  # noqa: E402

    return importlib.reload(rag_mod)


class TestPipeline:
    def test_retrieves_relevant_doc(self, rag):
        result = rag.answer("What is the capital of France?")
        assert result["retrieved"][0] == "doc-geo-1"
        assert "paris" in result["answer"].lower()
        assert result["citations"] == ["doc-geo-1"]

    def test_abstains_on_unanswerable(self, rag):
        result = rag.answer("What is the GDP of Mars in 1850?")
        assert result["answer"] == rag.ABSTAIN
        assert result["citations"] == []
        assert result["retrieved"] == []

    def test_broken_mode_degrades(self, monkeypatch):
        monkeypatch.setenv("AIPREFLIGHT_RAG_BROKEN", "1")
        import rag as rag_mod

        rag_mod = importlib.reload(rag_mod)
        result = rag_mod.answer("What is the capital of France?")
        assert result["retrieved"][0] != "doc-geo-1"


class TestRagProfile:
    def test_profile_loads(self):
        profile = load_profile(str(ROOT / "profiles" / "rag.yml"))
        assert profile["kind"] == "rag"
        assert profile["evals"]["min_pass_rate"] == 0.9

    def test_rag_requires_evals(self, tmp_path):
        p = tmp_path / "bad.yml"
        p.write_text("name: r\nkind: rag\ndeployment: {rollback_runbook: x}\n")
        with pytest.raises(ProfileError, match="must define an 'evals'"):
            load_profile(str(p))

    def test_rag_evals_must_gate(self, tmp_path):
        p = tmp_path / "bad.yml"
        p.write_text("name: r\nkind: rag\nevals: {command: 'x'}\n")
        with pytest.raises(ProfileError, match="must gate on results"):
            load_profile(str(p))
