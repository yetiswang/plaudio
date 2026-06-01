"""Searchable SQLite + FTS5 (trigram) corpus of locally-transcribed meetings.

Trigram tokeniser supports ZH+EN code-switched text (unicode61 fails on this).
"""
from __future__ import annotations
import json, os, pathlib, sqlite3
from datetime import datetime

def _normalize_segment(s: dict) -> dict:
    """Accept either the canonical {start_time, end_time, speaker, content} (ms)
    schema or the raw mlx-whisper {start, end, text} (seconds) schema.

    Canonical schema is returned. Speaker defaults to 'Unknown' when absent.
    """
    if "start_time" in s and "content" in s:
        return {
            "start_time": int(s["start_time"]),
            "end_time": int(s["end_time"]),
            "speaker": s.get("speaker", "Unknown"),
            "content": s["content"],
        }
    # Raw mlx-whisper layout: seconds + 'text'
    return {
        "start_time": int(float(s.get("start", 0)) * 1000),
        "end_time": int(float(s.get("end", 0)) * 1000),
        "speaker": s.get("speaker", "Unknown"),
        "content": (s.get("content") or s.get("text") or "").strip(),
    }


SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
  id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  title TEXT NOT NULL,
  duration_ms INTEGER,
  language TEXT,
  n_speakers INTEGER,
  audio_path TEXT,
  vault_note_path TEXT,
  source_file TEXT,
  ingested_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date);

CREATE TABLE IF NOT EXISTS segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  seg_idx INTEGER NOT NULL,
  start_ms INTEGER NOT NULL,
  end_ms INTEGER NOT NULL,
  speaker_label TEXT NOT NULL,
  speaker_name TEXT,
  content TEXT NOT NULL,
  UNIQUE(meeting_id, seg_idx)
);
CREATE INDEX IF NOT EXISTS idx_seg_meeting ON segments(meeting_id);
CREATE INDEX IF NOT EXISTS idx_seg_speaker ON segments(speaker_name);

CREATE TABLE IF NOT EXISTS speakers (
  meeting_id TEXT NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  real_name TEXT,
  duration_s REAL,
  PRIMARY KEY (meeting_id, label)
);

CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts USING fts5(
  content, content='segments', content_rowid='id', tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS segments_ai AFTER INSERT ON segments BEGIN
  INSERT INTO segments_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS segments_ad AFTER DELETE ON segments BEGIN
  INSERT INTO segments_fts(segments_fts, rowid, content) VALUES('delete', old.id, old.content);
END;
"""


class TranscriptCorpus:
    def __init__(self, db_path: pathlib.Path):
        self.db_path = pathlib.Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def default_path(cls) -> pathlib.Path:
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            return pathlib.Path(xdg).expanduser() / "plaudio" / "transcripts.db"
        return pathlib.Path("~/Library/Application Support/plaudio/transcripts.db").expanduser()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA)
        return conn

    def ingest(self, plaud_json: pathlib.Path, *,
               meeting_id: str, date: str, title: str,
               speakers: dict[str, str],
               vault_note: str | None = None, audio_path: str | None = None) -> None:
        plaud_json = pathlib.Path(plaud_json)
        data = json.loads(plaud_json.read_text())
        segs = [_normalize_segment(s) for s in data.get("segments", [])]
        meta = data.get("meta") or {}
        # Tolerate top-level language / n_speakers (raw mlx-whisper layout)
        if "language" not in meta and "language" in data:
            meta["language"] = data["language"]
        if "n_speakers" not in meta:
            meta["n_speakers"] = len({s["speaker"] for s in segs}) or None
        conn = self._connect()
        try:
            with conn:
                conn.execute("DELETE FROM segments WHERE meeting_id = ?", (meeting_id,))
                conn.execute("DELETE FROM speakers WHERE meeting_id = ?", (meeting_id,))
                conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
                conn.execute(
                    "INSERT INTO meetings (id, date, title, duration_ms, language, "
                    "n_speakers, audio_path, vault_note_path, source_file) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (meeting_id, date, title,
                     int(max((s["end_time"] for s in segs), default=0)),
                     meta.get("language"), meta.get("n_speakers"),
                     audio_path, vault_note, str(plaud_json)),
                )
                durs: dict[str, float] = {}
                for s in segs:
                    durs[s["speaker"]] = durs.get(s["speaker"], 0.0) + (s["end_time"] - s["start_time"]) / 1000.0
                for label, dur in durs.items():
                    conn.execute(
                        "INSERT INTO speakers (meeting_id, label, real_name, duration_s) VALUES (?, ?, ?, ?)",
                        (meeting_id, label, speakers.get(label), dur),
                    )
                for i, s in enumerate(segs):
                    conn.execute(
                        "INSERT INTO segments (meeting_id, seg_idx, start_ms, end_ms, "
                        "speaker_label, speaker_name, content) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (meeting_id, i, s["start_time"], s["end_time"],
                         s["speaker"], speakers.get(s["speaker"]), s["content"]),
                    )
        finally:
            conn.close()

    def search(self, query: str, *, speaker: str | None = None,
               since: str | None = None, until: str | None = None,
               limit: int = 50) -> list[dict]:
        conn = self._connect()
        try:
            q = ("SELECT m.date, m.title, s.start_ms, s.end_ms, s.speaker_name, "
                 "s.speaker_label, s.content, m.id "
                 "FROM segments_fts JOIN segments s ON s.id = segments_fts.rowid "
                 "JOIN meetings m ON m.id = s.meeting_id WHERE segments_fts MATCH ?")
            params: list = [query]
            if speaker:
                q += " AND (s.speaker_name = ? COLLATE NOCASE OR s.speaker_label = ?)"
                params += [speaker, speaker]
            if since:
                q += " AND m.date >= ?"
                params.append(since)
            if until:
                q += " AND m.date <= ?"
                params.append(until)
            q += " ORDER BY m.date DESC, s.start_ms ASC"
            if limit:
                q += f" LIMIT {int(limit)}"
            rows = conn.execute(q, params).fetchall()
            return [{"date": r[0], "title": r[1], "start_ms": r[2], "end_ms": r[3],
                     "speaker_name": r[4], "speaker_label": r[5], "content": r[6],
                     "meeting_id": r[7]} for r in rows]
        finally:
            conn.close()

    def list_meetings(self) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT m.id, m.date, m.title, m.duration_ms, m.language, m.n_speakers, "
                "(SELECT COUNT(*) FROM segments WHERE meeting_id=m.id), m.vault_note_path "
                "FROM meetings m ORDER BY m.date DESC, m.title").fetchall()
            return [{"id": r[0], "date": r[1], "title": r[2], "duration_ms": r[3],
                     "language": r[4], "n_speakers": r[5], "n_segments": r[6],
                     "vault_note_path": r[7]} for r in rows]
        finally:
            conn.close()
