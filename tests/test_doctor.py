import os, subprocess, sys
import shutil as _sh


def _plaudio(*args, env=None):
    if env is None:
        env = os.environ.copy()
    binary = _sh.which("plaudio")
    cmd = [binary] + list(args) if binary else [sys.executable, "-m", "plaudio.cli.main"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def test_doctor_runs_and_exits():
    r = _plaudio("doctor")
    assert r.returncode in (0, 1)
    combined = r.stdout + r.stderr
    assert "Plaudio doctor" in combined or "Plaudio" in combined or "doctor" in combined.lower()


def test_doctor_reports_missing_token(tmp_path):
    env = os.environ.copy()
    env["PLAUDIO_HF_TOKEN_FILE"] = str(tmp_path / "absent")
    r = _plaudio("doctor", env=env)
    combined = r.stdout + r.stderr
    assert "HF token" in combined
