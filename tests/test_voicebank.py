import json, os, pathlib, stat, pytest
from plaudio.core.voicebank import VoiceBank, VoiceProfile

def test_voiceprofile_required_fields():
    p = VoiceProfile(
        id="00000000-0000-0000-0000-000000000000",
        name="Alice Smith",
        embedding=[0.1] * 256,
        embedding_model="pyannote/speaker-diarization-3.1",
        embedding_dim=256,
        enrolled_from="fixtures/alice.wav",
        enrolled_at="2026-05-30T08:00:00Z",
        duration_s=45.0,
        n_speakers_in_audio=1,
        notes="self-recorded test sample",
    )
    assert p.name == "Alice Smith"
    assert len(p.embedding) == 256

def test_voicebank_empty_default(tmp_path):
    path = tmp_path / "voicebank.json"
    bank = VoiceBank.load(path)
    assert bank.schema_version == 1
    assert bank.profiles == []

def test_voicebank_save_roundtrip(tmp_path):
    path = tmp_path / "voicebank.json"
    bank = VoiceBank.load(path)
    bank.profiles.append(VoiceProfile(
        id="00000000-0000-0000-0000-000000000001",
        name="Bob Jones",
        embedding=[0.2] * 256,
        embedding_model="pyannote/speaker-diarization-3.1",
        embedding_dim=256,
        enrolled_from="fixtures/bob.wav",
        enrolled_at="2026-05-30T08:01:00Z",
        duration_s=30.0,
        n_speakers_in_audio=2,
        notes="",
    ))
    bank.save(path)
    re = VoiceBank.load(path)
    assert len(re.profiles) == 1
    assert re.profiles[0].name == "Bob Jones"

def test_voicebank_save_chmod_0600(tmp_path):
    path = tmp_path / "voicebank.json"
    bank = VoiceBank.load(path)
    bank.save(path)
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600, f"expected 0600, got {oct(mode)}"

def test_voicebank_refuses_unknown_schema_version(tmp_path):
    path = tmp_path / "voicebank.json"
    path.write_text(json.dumps({"schema_version": 999, "profiles": []}))
    with pytest.raises(ValueError, match="schema_version"):
        VoiceBank.load(path)
