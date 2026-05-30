"""Guard against accidentally shipping a populated vocab or NAME_CORRECTIONS."""
from plaudio.core.clean import DEFAULT_NAME_CORRECTIONS
from plaudio.core.transcribe import load_vocab_prompt
import pathlib

def test_default_name_corrections_empty():
    assert DEFAULT_NAME_CORRECTIONS == []

def test_default_vocab_prompt_empty_when_no_file(tmp_path):
    assert load_vocab_prompt(tmp_path / "absent.txt") == ""

def test_default_vocab_prompt_empty_for_empty_file(tmp_path):
    f = tmp_path / "vocab.txt"
    f.write_text("")
    assert load_vocab_prompt(f) == ""

def test_default_vocab_prompt_strips_comments(tmp_path):
    f = tmp_path / "vocab.txt"
    f.write_text("# comment-only file\n# nothing real\n")
    assert load_vocab_prompt(f) == ""
