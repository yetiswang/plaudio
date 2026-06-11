"""`plaudio doctor` -- environment + dependency checks. High-leverage support tool."""
from __future__ import annotations
import argparse, os, pathlib, platform, shutil, sys


def _ok(name: str, detail: str = "") -> None:
    print(f"  ok {name}" + (f": {detail}" if detail else ""))


def _bad(name: str, detail: str = "") -> int:
    print(f"  fail {name}" + (f" -- {detail}" if detail else ""))
    return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    print("Plaudio doctor -- environment check\n")
    fails = 0

    if platform.system() == "Darwin":
        _ok("macOS", platform.mac_ver()[0])
    else:
        fails |= _bad("platform", f"{platform.system()} (Plaudio supports macOS only)")

    if platform.machine() == "arm64":
        _ok("Apple Silicon", "arm64")
    else:
        fails |= _bad("CPU", f"{platform.machine()} (Apple Silicon required for mlx-whisper)")

    pv = sys.version_info
    if pv >= (3, 11):
        _ok("Python", f"{pv.major}.{pv.minor}.{pv.micro}")
    else:
        fails |= _bad("Python", f"{pv.major}.{pv.minor} (>= 3.11 required)")

    from plaudio.core.ffmpeg import REMEDIATION, resolve_ffmpeg_dir
    ff_dir = resolve_ffmpeg_dir()
    if ff_dir:
        on_path = shutil.which("ffmpeg")
        note = f"{ff_dir}/ffmpeg"
        if on_path and os.path.dirname(on_path) != ff_dir:
            note += f" (PATH ffmpeg at {on_path} is broken; using working fallback)"
        _ok("ffmpeg", note)
    else:
        fails |= _bad("ffmpeg", REMEDIATION)

    mw = shutil.which("mlx_whisper")
    if mw:
        _ok("mlx_whisper", mw)
    else:
        fails |= _bad("mlx_whisper", "not installed; pip install mlx-whisper")

    try:
        import pyannote.audio as _pa
        _ok("pyannote.audio", getattr(_pa, "__version__", "?"))
    except ImportError as e:
        fails |= _bad("pyannote.audio", f"import failed: {e}")

    token_path = pathlib.Path(
        os.environ.get("PLAUDIO_HF_TOKEN_FILE", "~/.huggingface/token")
    ).expanduser()
    if token_path.exists() and token_path.read_text().strip():
        _ok("HF token", str(token_path))
    else:
        fails |= _bad(
            "HF token",
            f"not found at {token_path}. pyannote/speaker-diarization-3.1 is gated; "
            f"accept at https://huggingface.co/pyannote/speaker-diarization-3.1 and "
            f"save your token at {token_path}",
        )

    try:
        import torch
        if torch.backends.mps.is_available():
            _ok("torch MPS", "available")
        else:
            print("  - torch MPS not available (will fall back to CPU; slower)")
    except ImportError:
        fails |= _bad("torch", "not installed")

    try:
        import torchcodec
        from torchcodec._core.ops import load_torchcodec_shared_libraries
        load_torchcodec_shared_libraries()
        _ok("torchcodec", f"{getattr(torchcodec, '__version__', '?')} (ffmpeg dylibs resolved)")
    except ImportError as e:
        fails |= _bad("torchcodec", f"import failed: {e}")
    except RuntimeError as e:
        first_line = str(e).splitlines()[0] if str(e) else "load_torchcodec_shared_libraries raised"
        fails |= _bad(
            "torchcodec",
            f"shared libraries did not load -- {first_line}. "
            f"Likely cause: Homebrew ffmpeg outpaced torchcodec's supported range "
            f"(torchcodec 0.7 supports ffmpeg 4-7; if `brew list ffmpeg` is >=8, "
            f"install a side-by-side version: `brew install ffmpeg@7 && brew pin ffmpeg@7`, "
            f"then symlink /opt/homebrew/opt/ffmpeg@7/lib/lib{{avutil.59,avcodec.61,"
            f"avformat.61,avfilter.10,avdevice.61,swresample.5,swscale.8}}.dylib "
            f"into /opt/homebrew/lib/",
        )

    print()
    if fails:
        print("Doctor: some checks failed. See messages above.")
        return 1
    print("Doctor: all checks passed.")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("doctor", help="environment + dependency check")
    p.set_defaults(func=cmd_doctor)
