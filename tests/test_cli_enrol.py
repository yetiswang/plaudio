import os, subprocess, sys
import shutil as _sh

def _plaudio(*args, env=None):
    if env is None:
        env = os.environ.copy()
    binary = _sh.which("plaudio")
    cmd = [binary] + list(args) if binary else [sys.executable, "-m", "plaudio.cli.main"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, env=env)

def test_cli_enrol_rejects_missing_audio_or_token(tmp_path):
    env = {**os.environ, "PLAUDIO_VOICEBANK": str(tmp_path / "vb.json")}
    r = _plaudio("enrol", str(tmp_path / "absent.mp3"),
                 "--name", "Alice Smith", "--start", "0", "--end", "30",
                 "--hf-token-file", str(tmp_path / "no-token"),
                 env=env)
    # Missing token file should be reported and exit non-zero.
    assert r.returncode != 0
    assert "HF token" in (r.stderr + r.stdout)
