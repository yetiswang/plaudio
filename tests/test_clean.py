import json, pathlib
from plaudio.core.clean import (
    DEFAULT_NAME_CORRECTIONS, load_corrections, apply_corrections,
    strip_silence_fillers, merge_fragments,
)

def test_default_name_corrections_is_empty():
    assert DEFAULT_NAME_CORRECTIONS == []

def test_load_corrections_from_json(tmp_path):
    f = tmp_path / "nc.json"
    f.write_text(json.dumps([["foo", "bar"], ["baz", "qux"]]))
    nc = load_corrections(f)
    assert nc == [("foo", "bar"), ("baz", "qux")]

def test_apply_corrections_substitution():
    nc = [("foo", "bar"), ("baz", "qux")]
    assert apply_corrections("foo baz", nc) == "bar qux"

def test_strip_silence_fillers():
    text = "yeah, yeah, yeah, yeah, yeah okay we go"
    cleaned = strip_silence_fillers(text)
    assert "yeah, yeah, yeah, yeah" not in cleaned

def test_merge_fragments_same_speaker_small_gap():
    segs = [
        {"speaker": "A", "t_start": 0, "t_end": 2, "text": "Hello there"},
        {"speaker": "A", "t_start": 3, "t_end": 5, "text": "how are you"},
    ]
    out = merge_fragments(segs)
    assert len(out) == 1
    assert out[0]["text"].startswith("Hello")
