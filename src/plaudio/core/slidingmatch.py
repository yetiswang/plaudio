"""Voice-bank-first sliding-window speaker labelling.

Algorithm: slide a 2s window across the audio with 1s hop, embed each window via
pyannote/embedding, cosine-match to enrolled profiles (averaged per name),
coalesce into runs, then overlay onto pre-existing transcript segments.
This bypasses pyannote's cluster-then-match merger failure on similar voices.
"""
from __future__ import annotations
import math
import pathlib
import warnings

DEFAULT_THRESHOLD = 0.55
DEFAULT_WINDOW_S = 2.0
DEFAULT_HOP_S = 1.0


def cosine(a, b) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def average_by_name(by_name: dict[str, list[list[float]]]) -> dict[str, list[float]]:
    """Average all embeddings under each name. Multi-sample-per-name is intentional."""
    out: dict[str, list[float]] = {}
    for name, embs in by_name.items():
        if not embs:
            continue
        dim = len(embs[0])
        s = [0.0] * dim
        for e in embs:
            for i, v in enumerate(e):
                s[i] += v
        n = len(embs)
        out[name] = [v / n for v in s]
    return out


def coalesce_runs(window_labels: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    """Merge consecutive same-label windows into [start, end, label] runs."""
    if not window_labels:
        return []
    runs = []
    cs, ce, cl = window_labels[0]
    for s, e, l in window_labels[1:]:
        if l == cl:
            ce = e
        else:
            runs.append((cs, ce, cl))
            cs, ce, cl = s, e, l
    runs.append((cs, ce, cl))
    return runs


def assign_speaker_to_segment(seg: dict, runs: list[tuple[float, float, str]]) -> str:
    """Pick the run covering the most of [seg.start_time, seg.end_time] (ms)."""
    s_start = seg["start_time"] / 1000.0
    s_end = seg["end_time"] / 1000.0
    best_overlap = 0.0
    best_label: str | None = None
    for rs, re_, rl in runs:
        if re_ < s_start or rs > s_end:
            continue
        ovl = min(re_, s_end) - max(rs, s_start)
        if ovl > best_overlap:
            best_overlap = ovl
            best_label = rl
    return best_label or "Unknown"


class SlidingMatcher:
    def __init__(
        self,
        bank,
        threshold: float = DEFAULT_THRESHOLD,
        window_s: float = DEFAULT_WINDOW_S,
        hop_s: float = DEFAULT_HOP_S,
    ):
        self.threshold = threshold
        self.window_s = window_s
        self.hop_s = hop_s
        self.means = average_by_name(bank.by_name())

    def label_segments(self, audio_path: pathlib.Path, segments: list[dict]) -> dict:
        """Re-label `segments` in place. Returns a small report dict."""
        if not self.means:
            return {
                "n_total": 0,
                "n_matched": 0,
                "n_segments_relabelled": 0,
                "note": "voicebank empty, all segments stay as-is",
            }
        from pyannote.audio import Inference

        warnings.filterwarnings("ignore")
        inf = Inference(
            "pyannote/embedding",
            window="sliding",
            duration=self.window_s,
            step=self.hop_s,
        )
        sliding = inf(str(audio_path))
        window_labels = []
        n_matched = 0
        for chunk, emb in zip(sliding.sliding_window, sliding.data):
            emb_list = (
                [float(x) for x in emb.flatten().tolist()]
                if hasattr(emb, "flatten")
                else list(emb)
            )
            best_name = None
            best_cos = -1.0
            for name, mean in self.means.items():
                c = cosine(emb_list, mean)
                if c > best_cos:
                    best_cos = c
                    best_name = name
            if best_cos >= self.threshold:
                window_labels.append((chunk.start, chunk.end, best_name))
                n_matched += 1
            else:
                window_labels.append((chunk.start, chunk.end, "Unknown"))
        runs = coalesce_runs(window_labels)
        n_rel = 0
        for s in segments:
            new_label = assign_speaker_to_segment(s, runs)
            if "original_speaker" not in s:
                s["original_speaker"] = s["speaker"]
            if s["speaker"] != new_label:
                n_rel += 1
            s["speaker"] = new_label
        return {
            "n_total": len(window_labels),
            "n_matched": n_matched,
            "n_segments_relabelled": n_rel,
            "n_runs": len(runs),
        }
