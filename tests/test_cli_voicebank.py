import json, os, subprocess, sys, pathlib
from plaudio.core.voicebank import VoiceBank

def _seeded_bank(tmp_path):
    path = tmp_path / "voicebank.json"
    bank = VoiceBank.load(path)
    bank.enrol(name="Alice", embedding=[0.1]*256, enrolled_from="a.wav",
               duration_s=30.0, n_speakers_in_audio=1, notes="", embedding_model="m")
    bank.enrol(name="Bob", embedding=[0.2]*256, enrolled_from="b.wav",
               duration_s=40.0, n_speakers_in_audio=2, notes="", embedding_model="m")
    bank.save(path)
    return path

def _plaudio(*args, env=None):
    """Invoke the plaudio CLI; works whether the plaudio script is on PATH or not."""
    if env is None:
        env = os.environ.copy()
    import shutil as _sh
    binary = _sh.which("plaudio")
    cmd = [binary] + list(args) if binary else [sys.executable, "-m", "plaudio.cli.main"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, env=env)

def test_cli_voicebank_list(tmp_path):
    bank_path = _seeded_bank(tmp_path)
    env = {**os.environ, "PLAUDIO_VOICEBANK": str(bank_path)}
    r = _plaudio("voicebank", "list", env=env)
    assert r.returncode == 0, r.stderr
    assert "Alice" in r.stdout
    assert "Bob" in r.stdout

def test_cli_voicebank_export(tmp_path):
    bank_path = _seeded_bank(tmp_path)
    out = tmp_path / "exported.json"
    env = {**os.environ, "PLAUDIO_VOICEBANK": str(bank_path)}
    r = _plaudio("voicebank", "export", str(out), env=env)
    assert r.returncode == 0
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["schema_version"] == 1
    assert len(data["profiles"]) == 2

def test_cli_voicebank_remove(tmp_path):
    bank_path = _seeded_bank(tmp_path)
    env = {**os.environ, "PLAUDIO_VOICEBANK": str(bank_path)}
    r = _plaudio("voicebank", "remove", "--name", "Alice", env=env)
    assert r.returncode == 0
    bank = VoiceBank.load(bank_path)
    assert [p.name for p in bank.profiles] == ["Bob"]
