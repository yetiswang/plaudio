"""`plaudio db ingest|search|list`"""
from __future__ import annotations
import argparse, os, pathlib, sys
from plaudio.core.corpus import TranscriptCorpus


def _corpus_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("PLAUDIO_CORPUS", str(TranscriptCorpus.default_path()))).expanduser()


def _parse_speaker_map(items: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def cmd_ingest(args: argparse.Namespace) -> int:
    corpus = TranscriptCorpus(_corpus_path())
    p = pathlib.Path(args.plaud_json).expanduser()
    if not p.exists():
        print(f"transcript not found: {p}", file=sys.stderr)
        return 2
    corpus.ingest(p,
                  meeting_id=args.meeting_id,
                  date=args.date,
                  title=args.title,
                  speakers=_parse_speaker_map(args.speaker),
                  vault_note=args.vault_note,
                  audio_path=args.audio_path)
    print(f"ingested meeting '{args.meeting_id}'")
    return 0


def _fmt_ms(ms: int) -> str:
    s = ms // 1000
    return f"{s//60:02d}:{s%60:02d}"


def cmd_search(args: argparse.Namespace) -> int:
    corpus = TranscriptCorpus(_corpus_path())
    rows = corpus.search(args.query, speaker=args.speaker,
                         since=args.since, until=args.until, limit=args.limit)
    if not rows:
        print("(no matches)")
        return 0
    last = None
    for r in rows:
        if r["meeting_id"] != last:
            print(f"\n-- {r['date']} | {r['title']} ({r['meeting_id']}) --")
            last = r["meeting_id"]
        speaker = r["speaker_name"] or r["speaker_label"]
        print(f"  [{_fmt_ms(r['start_ms'])}-{_fmt_ms(r['end_ms'])}] {speaker}: {r['content'][:200]}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    corpus = TranscriptCorpus(_corpus_path())
    rows = corpus.list_meetings()
    if not rows:
        print("(empty)")
        return 0
    for r in rows:
        dur = f"{(r['duration_ms'] or 0)/60000:.1f}min" if r['duration_ms'] else "?"
        print(f"  {r['date']}  {r['title'][:55]:<55s}  {dur:>8s}  "
              f"{(r['language'] or '?'):>4s}  {str(r['n_speakers'] or '?'):>2s}sp  {r['n_segments']:>5d}seg")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    db = sub.add_parser("db", help="searchable transcripts corpus")
    dbsub = db.add_subparsers(dest="db_cmd", required=True)

    i = dbsub.add_parser("ingest", help="ingest a .plaud.json transcript into the corpus")
    i.add_argument("plaud_json", help="path to .plaud.json file")
    i.add_argument("--meeting-id", required=True, help="unique meeting identifier")
    i.add_argument("--date", required=True, help="meeting date YYYY-MM-DD")
    i.add_argument("--title", required=True, help="meeting title")
    i.add_argument("--vault-note", help="path to vault note for this meeting")
    i.add_argument("--audio-path", help="path to source audio file")
    i.add_argument("--speaker", action="append", metavar="LABEL=Name",
                   help="speaker label to real-name mapping; repeat for multiple")
    i.set_defaults(func=cmd_ingest)

    s = dbsub.add_parser("search", help="full-text search across transcripts")
    s.add_argument("query", help="search query (trigram, supports ZH+EN)")
    s.add_argument("--speaker", help="filter to a specific speaker name or label")
    s.add_argument("--since", metavar="YYYY-MM-DD", help="earliest meeting date")
    s.add_argument("--until", metavar="YYYY-MM-DD", help="latest meeting date")
    s.add_argument("--limit", type=int, default=50, help="max results (default 50)")
    s.set_defaults(func=cmd_search)

    lst = dbsub.add_parser("list", help="list all ingested meetings")
    lst.set_defaults(func=cmd_list)
