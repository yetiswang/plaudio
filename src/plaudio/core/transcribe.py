"""mlx-whisper wrapper. Vocab/initial-prompt anchoring. Empty default vocab."""
from __future__ import annotations
import dataclasses, json, pathlib, subprocess, time

from .ffmpeg import REMEDIATION, ffmpeg_env

DEFAULT_MODEL = "mlx-community/whisper-large-v3-mlx"


@dataclasses.dataclass
class ASRSegment:
    text: str
    start_s: float
    end_s: float


def load_vocab_prompt(vocab_file: pathlib.Path) -> str:
    """Read a vocab file (one term per line, # comments ok) into a Whisper initial prompt.

    Returns empty string if the file is absent or has only comments/blanks.
    """
    if not vocab_file.exists():
        return ""
    terms = []
    for line in vocab_file.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        terms.append(s)
    if not terms:
        return ""
    return ", ".join(terms) + "."


def transcribe(
    audio: pathlib.Path,
    *,
    out_dir: pathlib.Path,
    language: str = "en",
    vocab: str = "",
    model: str = DEFAULT_MODEL,
) -> tuple[list[ASRSegment], float]:
    """Run mlx-whisper on audio, return (segments, elapsed_seconds)."""
    audio = pathlib.Path(audio)
    if not audio.exists():
        raise FileNotFoundError(audio)
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "mlx_whisper", str(audio),
        "--model", model,
        "--language", language,
        "--output-format", "json",
        "--output-dir", str(out_dir),
        "--condition-on-previous-text", "False",
        "--hallucination-silence-threshold", "2.0",
    ]
    if vocab:
        cmd += ["--initial-prompt", vocab]
    # mlx-whisper shells out to bare `ffmpeg`; make sure it sees a working one.
    env, ffmpeg_dir = ffmpeg_env()
    if ffmpeg_dir is None:
        raise RuntimeError(REMEDIATION)
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    elapsed = time.time() - t0
    if result.returncode != 0:
        raise RuntimeError(f"mlx_whisper failed (exit {result.returncode}):\n{result.stderr}")
    out_file = out_dir / f"{audio.stem}.json"
    if not out_file.exists():
        # mlx-whisper exits 0 but writes nothing when ffmpeg fails to decode the
        # audio (it catches the dyld error and skips the file). Surface that.
        raise RuntimeError(
            f"mlx_whisper completed but no output at {out_file}. "
            f"Used ffmpeg from {ffmpeg_dir}. If audio decode failed, "
            f"the resolved ffmpeg may be broken.\n{REMEDIATION}"
        )
    data = json.loads(out_file.read_text())
    segs = [
        ASRSegment(
            text=(s.get("text") or "").strip(),
            start_s=float(s.get("start", 0)),
            end_s=float(s.get("end", 0)),
        )
        for s in data.get("segments", [])
    ]
    return segs, elapsed
