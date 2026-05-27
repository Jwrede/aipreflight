"""Tests for `aipreflight doctor` and its environment checks."""

import aipreflight.doctor as doctor
from aipreflight import EXIT_CONFIG, EXIT_PASS
from aipreflight.checks import FAIL, PASS, SKIP, WARN
from aipreflight.cli import main


class TestPython:
    def test_current_interpreter_passes(self):
        # The test runner already satisfies the minimum, so this must pass.
        assert doctor.check_python().status == PASS


class TestLlmprobe:
    def test_missing_warns(self, monkeypatch):
        monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
        r = doctor.check_llmprobe()
        assert r.status == WARN
        assert "not found" in r.summary

    def test_present_compatible_passes(self, monkeypatch):
        monkeypatch.setattr(doctor.shutil, "which", lambda _: "/usr/bin/llmprobe")
        monkeypatch.setattr(doctor, "_llmprobe_version", lambda: "llmprobe version 1.4.0")
        r = doctor.check_llmprobe()
        assert r.status == PASS
        assert "1.4.0" in r.summary

    def test_present_too_old_warns(self, monkeypatch):
        monkeypatch.setattr(doctor.shutil, "which", lambda _: "/usr/bin/llmprobe")
        monkeypatch.setattr(doctor, "_llmprobe_version", lambda: "llmprobe v1.2.3")
        r = doctor.check_llmprobe()
        assert r.status == WARN
        assert "1.2.3" in r.summary

    def test_present_unknown_version_warns(self, monkeypatch):
        monkeypatch.setattr(doctor.shutil, "which", lambda _: "/usr/bin/llmprobe")
        monkeypatch.setattr(doctor, "_llmprobe_version", lambda: "")
        assert doctor.check_llmprobe().status == WARN


class TestTokentoll:
    def test_missing_warns(self, monkeypatch):
        monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
        assert doctor.check_tokentoll().status == WARN

    def test_present_passes(self, monkeypatch):
        monkeypatch.setattr(doctor.shutil, "which", lambda _: "/usr/bin/tokentoll")
        assert doctor.check_tokentoll().status == PASS


class TestProfiles:
    def test_shipped_profiles_parse(self):
        r = doctor.check_profiles(doctor.DEFAULT_PROFILES)
        assert r.status == PASS

    def test_malformed_profile_fails(self, tmp_path):
        bad = tmp_path / "bad.yml"
        bad.write_text("name: app\n  bad: : :\n")
        r = doctor.check_profiles([str(bad)])
        assert r.status == FAIL

    def test_no_profiles_skips(self, tmp_path):
        r = doctor.check_profiles([str(tmp_path / "missing.yml")])
        assert r.status == SKIP


class TestRunDoctor:
    def test_names_and_prometheus_optional(self, monkeypatch):
        monkeypatch.setattr(doctor.shutil, "which", lambda _: None)
        names = [r.name for r in doctor.run_doctor()]
        assert names == ["python", "llmprobe", "tokentoll", "profiles"]
        with_prom = [r.name for r in doctor.run_doctor(prometheus="http://x:9090")]
        assert with_prom[-1] == "prometheus"


class TestCli:
    def test_doctor_ready_exit_zero(self, monkeypatch, capsys):
        from aipreflight.checks import CheckResult

        monkeypatch.setattr(
            "aipreflight.doctor.run_doctor",
            lambda *a, **k: [CheckResult("python", PASS, "ok"), CheckResult("llmprobe", WARN, "missing")],
        )
        assert main(["doctor"]) == EXIT_PASS
        assert "Environment: READY" in capsys.readouterr().out

    def test_doctor_failure_exit_config(self, monkeypatch, capsys):
        from aipreflight.checks import CheckResult

        monkeypatch.setattr(
            "aipreflight.doctor.run_doctor",
            lambda *a, **k: [CheckResult("python", FAIL, "too old")],
        )
        assert main(["doctor"]) == EXIT_CONFIG
        assert "Environment: NOT READY" in capsys.readouterr().out
