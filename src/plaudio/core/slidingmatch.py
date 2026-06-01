"""Voice-bank-first sliding-window speaker labelling.

Algorithm: slide a 2s window across the audio with 1s hop, embed each window
through the same speaker-embedder used by `pyannote/speaker-diarization-3.1`
(which is also what `plaudio enrol` uses via `diarise_with_embeddings`), cosine-
match to enrolled profiles (averaged per name), coalesce into runs, then overlay
onto pre-existing transcript segments. This bypasses pyannote's cluster-then-
match merger failure on similar voices.

Why `pyannote/wespeaker-voxceleb-resnet34-LM` (256-dim) and NOT `pyannote/
embedding` (512-dim in pyannote 4.x):

  Before this commit, slidingmatch used `pyannote/embedding` standalone. That
  was the right model under pyannote 3.x (256-dim) but pyannote 4.x updated
  `pyannote/embedding` to a larger 512-dim model while the speaker-diarization
  -3.1 pipeline kept its 256-dim wespeaker embedder for backwards compat.
  Result: enrol produced 256-dim profiles, match extracted 512-dim windows —
  cosine sim = 0.0 across the board, silent zero-match runs.

  Aligning both code paths on `pyannote/wespeaker-voxceleb-resnet34-LM` (the
  exact model the pipeline bundles) restores consistency. Origin: 2026-06-01.

pyannote 4.x API note: `Inference` requires a Model instance, not a string.
Load via `Model.from_pretrained()`. The model is gated; HF token resolution
via `HF_TOKEN` env, `HUGGINGFACE_TOKEN` env, then `~/.huggingface/token`.
"""
from __future__ import annotations
import math
import os
import pathlib
import warnings

DEFAULT_THRESHOLD = 0.55
DEFAULT_WINDOW_S = 2.0
DEFAULT_HOP_S = 1.0


def _get_hf_token() -> str | None:
    """Look up HF token: env var first, then ~/.huggingface/token."""
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if tok:
        return tok.strip()
    p = pathlib.Path.home() / ".huggingface" / "token"
    if p.exists():
        return p.read_text().strip() or None
    return None


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
        from pyannote.audio import Model, Inference

        warnings.filterwarnings("ignore")
        # Use the SAME embedder as `plaudio enrol` (which loads it transitively
        # via pyannote/speaker-diarization-3.1). The pipeline pins its embedder
        # to `pyannote/wespeaker-voxceleb-resnet34-LM` — 256-dim. Loading the
        # same model directly here keeps match/enrol embeddings dim-compatible.
        # See module docstring for the why.
        hf_token = _get_hf_token()
        try:
            model = Model.from_pretrained(
                "pyannote/wespeaker-voxceleb-resnet34-LM", token=hf_token
            )
        except Exception as e:
            raise RuntimeError(
                "Failed to load pyannote/wespeaker-voxceleb-resnet34-LM. If this "
                "is a 403/GatedRepoError, visit https://huggingface.co/pyannote/"
                "wespeaker-voxceleb-resnet34-LM and accept the model terms with "
                "the same HF account whose token plaudio is using (env HF_TOKEN "
                "or ~/.huggingface/token). Original error: " + str(e)
            ) from e
        try:
            import torch
            if torch.backends.mps.is_available():
                model.to(torch.device("mps"))
        except Exception:
            pass
        inf = Inference(
            model,
            window="sliding",
            duration=self.window_s,
            step=self.hop_s,
        )
        sliding = inf(str(audio_path))
        window_labels = []
        n_matched = 0
        # Dim-mismatch check: pyannote 3.x emitted 256-dim from pyannote/embedding;
        # pyannote 4.x emits 512-dim. A voicebank enrolled under an older version
        # will silently produce zero matches (cosine() returns 0.0 on dim mismatch).
        # Detect once on the first window and surface an actionable error.
        first_window_dim: int | None = None
        bank_dim = len(next(iter(self.means.values())))
        for chunk, emb in zip(sliding.sliding_window, sliding.data):
            emb_list = (
                [float(x) for x in emb.flatten().tolist()]
                if hasattr(emb, "flatten")
                else list(emb)
            )
            if first_window_dim is None:
                first_window_dim = len(emb_list)
                if first_window_dim != bank_dim:
                    raise RuntimeError(
                        f"Voicebank/embedding dim mismatch: bank has {bank_dim}-dim "
                        f"profiles but current pyannote/embedding model emits "
                        f"{first_window_dim}-dim. The bank was built under a "
                        f"different pyannote-audio version. Regenerate the bank by "
                        f"re-enrolling each voice with `plaudio enrol` under the "
                        f"current install (pyannote 3.x → 4.x typically changes "
                        f"256 → 512). Original samples per voice should be kept; "
                        f"see 90-Archive/voice-bank/ on Yuyang's setup."
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
