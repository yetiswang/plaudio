"""End-to-end integration test. Opt-in via: pytest -m integration"""
import json, os, pathlib, subprocess, sys, pytest
import shutil as _sh

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

def _plaudio(*args, env=None):
    if env is None:
        env = os.environ.copy()
    binary = _sh.which("plaudio")
    cmd = [binary] + list(args) if binary else [sys.executable, "-m", "plaudio.cli.main"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, env=env)

@pytest.mark.integration
def test_end_to_end_quickstart(tmp_path):
    audio = FIXTURES / "self-30s.wav"
    if not audio.exists():
        pytest.skip("self-30s.wav not present (see tests/fixtures/CONSENT-LOG.md)")
    env = {**os.environ,
           "PLAUDIO_VOICEBANK": str(tmp_path / "vb.json"),
           "PLAUDIO_CORPUS": str(tmp_path / "tx.db")}
    r = _plaudio("transcribe", str(audio), "--out", str(tmp_path), env=env)
    assert r.returncode == 0, r.stderr
    asr = tmp_path / f"{audio.stem}.json"
    assert asr.exists()
    data = json.loads(asr.read_text())
    segs = [{"start_time": int(s["start"] * 1000), "end_time": int(s["end"] * 1000),
             "speaker": "Speaker 1", "content": s["text"]}
            for s in data.get("segments", [])]
    plaud_json = tmp_path / f"{audio.stem}.plaud.json"
    plaud_json.write_text(json.dumps({"meta": {"language": "en", "n_speakers": 1},
                                       "segments": segs}))
    r = _plaudio("db", "ingest", str(plaud_json),
                 "--meeting-id", "INTEGRATION_TEST", "--date", "2026-05-30",
                 "--title", "integration", env=env)
    assert r.returncode == 0, r.stderr
    r = _plaudio("db", "list", env=env)
    assert "INTEGRATION_TEST" in r.stdout
