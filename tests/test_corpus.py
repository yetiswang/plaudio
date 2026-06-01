import json, pathlib, pytest
from plaudio.core.corpus import TranscriptCorpus

SAMPLE = {
    "meta": {"language": "en", "n_speakers": 2},
    "segments": [
        {"start_time": 0, "end_time": 2000, "speaker": "Alice", "content": "hello world"},
        {"start_time": 2000, "end_time": 5000, "speaker": "Bob", "content": "foundation model"},
        {"start_time": 5000, "end_time": 8000, "speaker": "Alice", "content": "你好 nanolab"},
    ],
}


def test_ingest_creates_meeting(tmp_path):
    corpus = TranscriptCorpus(tmp_path / "tx.db")
    sample = tmp_path / "x.plaud.json"
    sample.write_text(json.dumps(SAMPLE))
    corpus.ingest(sample, meeting_id="M1", date="2026-05-30", title="Test", speakers={})
    rows = corpus.list_meetings()
    assert rows[0]["id"] == "M1"
    assert rows[0]["title"] == "Test"


def test_ingest_idempotent_on_meeting_id(tmp_path):
    corpus = TranscriptCorpus(tmp_path / "tx.db")
    sample = tmp_path / "x.plaud.json"
    sample.write_text(json.dumps(SAMPLE))
    corpus.ingest(sample, meeting_id="M1", date="2026-05-30", title="T", speakers={})
    corpus.ingest(sample, meeting_id="M1", date="2026-05-30", title="T", speakers={})
    assert len(corpus.list_meetings()) == 1


def test_search_trigram_finds_substring(tmp_path):
    corpus = TranscriptCorpus(tmp_path / "tx.db")
    sample = tmp_path / "x.plaud.json"
    sample.write_text(json.dumps(SAMPLE))
    corpus.ingest(sample, meeting_id="M1", date="2026-05-30", title="T", speakers={})
    hits = corpus.search("nanolab")
    assert len(hits) == 1
    assert "nanolab" in hits[0]["content"]


def test_search_speaker_filter(tmp_path):
    corpus = TranscriptCorpus(tmp_path / "tx.db")
    sample = tmp_path / "x.plaud.json"
    sample.write_text(json.dumps(SAMPLE))
    corpus.ingest(sample, meeting_id="M1", date="2026-05-30", title="T", speakers={})
    hits = corpus.search("foundation", speaker="Bob")
    assert len(hits) == 1
    hits2 = corpus.search("foundation", speaker="Alice")
    assert len(hits2) == 0


def test_ingest_accepts_raw_mlx_whisper_schema(tmp_path):
    """plaudio transcribe outputs {start, end, text} (seconds) + top-level language.
    corpus.ingest must tolerate this so the diarisation-merge step doesn't have
    to remap field names. Schema-shim regression test (origin: 2026-06-01)."""
    raw = {
        "language": "en",
        "segments": [
            {"start": 0.0, "end": 2.5, "speaker": "Alice", "text": "raw schema works"},
            {"start": 2.5, "end": 5.0, "speaker": "Bob", "text": "nanolab raw entry"},
        ],
    }
    corpus = TranscriptCorpus(tmp_path / "tx.db")
    sample = tmp_path / "raw.plaud.json"
    sample.write_text(json.dumps(raw))
    corpus.ingest(sample, meeting_id="RAW", date="2026-06-01", title="Raw", speakers={})
    rows = corpus.list_meetings()
    assert rows[0]["id"] == "RAW"
    assert rows[0]["language"] == "en"
    assert rows[0]["n_speakers"] == 2
    hits = corpus.search("nanolab")
    assert any("nanolab" in h["content"] for h in hits)


def test_ingest_accepts_segment_without_speaker(tmp_path):
    """If diarisation skipped, segments may lack 'speaker'; treat as 'Unknown'."""
    raw = {"segments": [{"start": 0.0, "end": 1.0, "text": "anonymous chunk"}]}
    corpus = TranscriptCorpus(tmp_path / "tx.db")
    sample = tmp_path / "nospeak.plaud.json"
    sample.write_text(json.dumps(raw))
    corpus.ingest(sample, meeting_id="NS", date="2026-06-01", title="NS", speakers={})
    hits = corpus.search("anonymous")
    assert any("anonymous" in h["content"] for h in hits)
