import pathlib, pytest
from plaudio.core.diarise import DiariseResult

def test_diariseresult_dataclass_shape():
    r = DiariseResult(
        turns=[(0.0, 1.0, "SPEAKER_00")],
        embeddings_by_label={"SPEAKER_00": [0.1]*256},
        elapsed_s=1.5,
    )
    assert r.turns == [(0.0, 1.0, "SPEAKER_00")]
    assert "SPEAKER_00" in r.embeddings_by_label

def test_diarise_rejects_missing_token(tmp_path):
    from plaudio.core.diarise import diarise
    with pytest.raises(ValueError, match="HF token"):
        diarise(tmp_path / "x.mp3", hf_token="", num_speakers=2)

def test_diarise_with_embeddings_rejects_missing_token(tmp_path):
    from plaudio.core.diarise import diarise_with_embeddings
    with pytest.raises(ValueError, match="HF token"):
        diarise_with_embeddings(tmp_path / "x.mp3", hf_token="", num_speakers=2)
