import pathlib, pytest
from plaudio.core.transcribe import transcribe, load_vocab_prompt


def test_load_vocab_prompt_empty_by_default(tmp_path):
    assert load_vocab_prompt(tmp_path / "absent.txt") == ""


def test_load_vocab_prompt_joins_terms(tmp_path):
    f = tmp_path / "vocab.txt"
    f.write_text("alpha\nbeta\n\n# comment\ngamma\n")
    prompt = load_vocab_prompt(f)
    assert prompt == "alpha, beta, gamma."


def test_transcribe_rejects_missing_audio(tmp_path):
    with pytest.raises(FileNotFoundError):
        transcribe(tmp_path / "missing.mp3", out_dir=tmp_path)
