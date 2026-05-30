"""pyannote-audio 3.1 diarisation wrapper.

Workaround for the libavutil mismatch: pyannote 4.x defaults to torchcodec
which depends on libavutil 56/57 (ffmpeg 4/5). Homebrew ships ffmpeg 7+
(libavutil 59+). We sidestep by pre-converting the audio to 16 kHz mono WAV
via ffmpeg, then loading with soundfile, then passing as a dict
{waveform, sample_rate} to the pyannote pipeline.

Note on pyannote 4.x API: Pipeline.__call__ always returns a DiarizeOutput
object with .speaker_diarization (Annotation) and .speaker_embeddings (ndarray).
The return_embeddings kwarg used in older code is not supported; embeddings are
always present in the output.
"""
from __future__ import annotations
import dataclasses, pathlib, subprocess, tempfile, time


@dataclasses.dataclass
class DiariseResult:
    turns: list[tuple[float, float, str]]
    embeddings_by_label: dict[str, list[float]]  # empty unless return_embeddings=True
    elapsed_s: float


def _pre_convert(audio: pathlib.Path) -> pathlib.Path:
    wav = pathlib.Path(tempfile.mktemp(suffix=".wav"))
    conv = subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(audio), "-ac", "1", "-ar", "16000", str(wav)
    ], capture_output=True, text=True)
    if conv.returncode != 0:
        raise RuntimeError(f"ffmpeg pre-convert failed: {conv.stderr}")
    return wav


def _load_pipeline(hf_token: str):
    from pyannote.audio import Pipeline
    import torch
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=hf_token,
    )
    if torch.backends.mps.is_available():
        pipeline.to(torch.device("mps"))
    return pipeline


def _load_waveform(wav: pathlib.Path):
    import torch, soundfile as sf
    samples, sample_rate = sf.read(str(wav))
    waveform = torch.from_numpy(samples).float()
    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)
    return waveform, sample_rate


def diarise(
    audio: pathlib.Path,
    *,
    hf_token: str,
    num_speakers: int | None = None,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> DiariseResult:
    if not hf_token:
        raise ValueError("HF token is required (pyannote/speaker-diarization-3.1 is gated)")
    audio = pathlib.Path(audio)
    pipeline = _load_pipeline(hf_token)
    wav = _pre_convert(audio)
    try:
        waveform, sr = _load_waveform(wav)
        kwargs: dict = {}
        if num_speakers is not None:
            kwargs["num_speakers"] = num_speakers
        else:
            if min_speakers is not None:
                kwargs["min_speakers"] = min_speakers
            if max_speakers is not None:
                kwargs["max_speakers"] = max_speakers
        t0 = time.time()
        output = pipeline({"waveform": waveform, "sample_rate": sr}, **kwargs)
        elapsed = time.time() - t0
    finally:
        wav.unlink(missing_ok=True)
    # pyannote 4.x always returns DiarizeOutput; .speaker_diarization is the Annotation
    diary = output.speaker_diarization
    turns = [
        (t.start, t.end, sp)
        for t, _, sp in diary.itertracks(yield_label=True)
    ]
    return DiariseResult(turns=turns, embeddings_by_label={}, elapsed_s=elapsed)


def diarise_with_embeddings(
    audio: pathlib.Path,
    *,
    hf_token: str,
    num_speakers: int | None = None,
) -> DiariseResult:
    """Same as diarise(), but also returns per-speaker mean embeddings. Used by enrol.

    pyannote 4.x always returns embeddings in DiarizeOutput.speaker_embeddings;
    speaker order matches output.speaker_diarization.labels().
    """
    if not hf_token:
        raise ValueError("HF token is required (pyannote/speaker-diarization-3.1 is gated)")
    audio = pathlib.Path(audio)
    pipeline = _load_pipeline(hf_token)
    wav = _pre_convert(audio)
    try:
        waveform, sr = _load_waveform(wav)
        kwargs: dict = {}
        if num_speakers is not None:
            kwargs["num_speakers"] = num_speakers
        t0 = time.time()
        output = pipeline({"waveform": waveform, "sample_rate": sr}, **kwargs)
        elapsed = time.time() - t0
    finally:
        wav.unlink(missing_ok=True)
    diary = output.speaker_diarization
    turns = [
        (t.start, t.end, sp)
        for t, _, sp in diary.itertracks(yield_label=True)
    ]
    labels = diary.labels()
    emb: dict[str, list[float]] = {}
    if output.speaker_embeddings is not None:
        for i, label in enumerate(labels):
            if i < len(output.speaker_embeddings):
                emb[label] = [float(x) for x in output.speaker_embeddings[i].flatten().tolist()]
    return DiariseResult(turns=turns, embeddings_by_label=emb, elapsed_s=elapsed)
