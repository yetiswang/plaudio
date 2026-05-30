"""`plaudio clean TRANSCRIPT_MD [--corrections FILE]`"""
from __future__ import annotations
import argparse, pathlib, re, sys
from plaudio.core.clean import (
    load_corrections, apply_corrections, strip_silence_fillers,
    merge_fragments, reflow_speaker_paragraphs, fmt_ts, wrap_para,
)

TRANSCRIPT_RE = re.compile(r"^## Transcript\s*$", re.M)
SEG_RE = re.compile(
    r"\*\*\[(\d+):(\d+)[–—\-](\d+):(\d+)\] ([^*:]+):\*\* "
    r"((?:.|\n(?!\*\*\[))+?)(?=\n\*\*\[|\Z)",
    re.MULTILINE,
)
NEXT_SECTION_RE = re.compile(r"^## (?!Transcript)", re.M)

def parse_transcript_block(content: str):
    m_start = TRANSCRIPT_RE.search(content)
    if not m_start:
        return [], -1, -1
    rest = content[m_start.end():]
    m_next = NEXT_SECTION_RE.search(rest)
    end_idx = m_start.end() + (m_next.start() if m_next else len(rest))
    block = content[m_start.end():end_idx]
    segments = []
    for match in SEG_RE.finditer(block):
        m1, s1, m2, s2, speaker, text = match.groups()
        segments.append({
            "speaker": speaker.strip(),
            "t_start": int(m1) * 60 + int(s1),
            "t_end": int(m2) * 60 + int(s2),
            "text": " ".join(text.split()),
        })
    return segments, m_start.start(), end_idx

def render_transcript(segments, meta_line):
    lines = ["## Transcript", "", meta_line, ""]
    for seg in segments:
        if not seg["text"].strip(): continue
        lines.append(f"**[{fmt_ts(seg['t_start'])}–{fmt_ts(seg['t_end'])}] {seg['speaker']}:** "
                     f"{wrap_para(seg['text'])}")
        lines.append("")
    return "\n".join(lines)

def cmd_clean(args: argparse.Namespace) -> int:
    path = pathlib.Path(args.path).expanduser()
    if not path.exists():
        print(f"not found: {path}", file=sys.stderr); return 2
    corrections = load_corrections(pathlib.Path(args.corrections).expanduser()) if args.corrections else []
    content = path.read_text()
    if "<!-- cleaned: true -->" in content and not args.force:
        print(f"  skip (already cleaned): {path.name}")
        return 0
    segments, start, end = parse_transcript_block(content)
    if not segments:
        print(f"  no transcript block found: {path.name}", file=sys.stderr); return 1
    for seg in segments:
        seg["text"] = apply_corrections(seg["text"], corrections)
        seg["text"] = strip_silence_fillers(seg["text"])
        seg["text"] = re.sub(r"\s+", " ", seg["text"]).strip()
    segments = merge_fragments(segments)
    segments = reflow_speaker_paragraphs(segments)
    meta_line = "*Local pipeline transcript. Cleaned for readability.*"
    new_block = render_transcript(segments, meta_line) + "\n<!-- cleaned: true -->\n"
    path.write_text(content[:start] + new_block + content[end:])
    print(f"  cleaned: {path.name}")
    return 0

def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("clean", help="clean a transcript markdown file")
    p.add_argument("path")
    p.add_argument("--corrections", help="path to a JSON list of [wrong, right] pairs")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_clean)
