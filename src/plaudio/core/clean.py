"""Transcript cleaning: empty default NAME_CORRECTIONS, sentence merging, filler strip.

CRITICAL: DEFAULT_NAME_CORRECTIONS is intentionally empty in the public package.
Users (including the vault adapter) load their own corrections via
load_corrections(path). NEVER ship a populated table here.
"""
from __future__ import annotations
import json, pathlib, re, textwrap

DEFAULT_NAME_CORRECTIONS: list[tuple[str, str]] = []  # MUST stay empty

FILLER_PATTERN = re.compile(
    r"\b(yeah|yes|okay|ok|right|so|thank you|thanks|um|uh|hmm|mm|mhm)"
    r"(?:[,.]?\s+\1){3,}\b",
    re.IGNORECASE,
)
SENTENCE_END = ".!?…"

def load_corrections(path: pathlib.Path) -> list[tuple[str, str]]:
    """Load NAME_CORRECTIONS from a JSON file (list of [wrong, right] pairs).

    Returns empty list if the file is absent.
    """
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    return [(item[0], item[1]) for item in raw if isinstance(item, (list, tuple)) and len(item) == 2]

def apply_corrections(text: str, corrections: list[tuple[str, str]]) -> str:
    for wrong, right in corrections:
        text = text.replace(wrong, right)
    return text

def strip_silence_fillers(text: str) -> str:
    return FILLER_PATTERN.sub(lambda m: m.group(1), text)

def merge_fragments(segments: list[dict]) -> list[dict]:
    if not segments:
        return []
    out = [dict(segments[0])]
    for seg in segments[1:]:
        prev = out[-1]
        same_speaker = seg["speaker"] == prev["speaker"]
        gap = seg["t_start"] - prev["t_end"]
        prev_last = prev["text"][-1] if prev["text"] else ""
        next_first = seg["text"][:1]
        joins = prev_last not in SENTENCE_END and next_first.islower()
        if same_speaker and (gap <= 5 or joins):
            prev["text"] = (prev["text"].rstrip() + " " + seg["text"].lstrip()).strip()
            prev["t_end"] = seg["t_end"]
        else:
            out.append(dict(seg))
    return out

def reflow_speaker_paragraphs(segments: list[dict]) -> list[dict]:
    if not segments:
        return []
    out = [dict(segments[0])]
    for seg in segments[1:]:
        prev = out[-1]
        if seg["speaker"] == prev["speaker"]:
            prev["text"] = (prev["text"].rstrip() + " " + seg["text"].lstrip()).strip()
            prev["t_end"] = seg["t_end"]
        else:
            out.append(dict(seg))
    return out

def fmt_ts(s: int) -> str:
    return f"{s // 60:02d}:{s % 60:02d}"

def wrap_para(text: str, width: int = 100) -> str:
    return textwrap.fill(text, width=width, subsequent_indent="  ")
