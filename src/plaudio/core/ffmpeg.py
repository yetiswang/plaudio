"""Resolve a *working* ffmpeg for the ASR subprocess.

Homebrew periodically promotes a new ffmpeg (e.g. 8.x) whose dylib ABI no longer
matches an already-upgraded dependency (the recurring x265 .215-vs-.216 mismatch),
leaving the system `ffmpeg` on PATH crashing with a dyld load error. mlx-whisper
shells out to bare `ffmpeg`, catches the failure, and silently skips the file, so
the only symptom upstream is "completed but no output". This module makes plaudio
robust to that: it prefers whatever `ffmpeg` already works, and otherwise falls
back to a pinned side-by-side build (`brew install ffmpeg@7 && brew pin ffmpeg@7`).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache

# Checked in order. Pinned side-by-side builds first as the stable fallback,
# then the usual Homebrew / system locations.
_CANDIDATE_DIRS = [
    "/opt/homebrew/opt/ffmpeg@7/bin",
    "/opt/homebrew/opt/ffmpeg@6/bin",
    "/usr/local/opt/ffmpeg@7/bin",
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/usr/bin",
]


def _works(ffmpeg_path: str) -> bool:
    """True if this ffmpeg binary actually launches (dylibs resolve)."""
    try:
        r = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return r.returncode == 0
    except Exception:
        return False


@lru_cache(maxsize=1)
def resolve_ffmpeg_dir() -> str | None:
    """Directory of a working ffmpeg, or None if none on the system works.

    1. The `ffmpeg` already on PATH, if it launches.
    2. Known candidate dirs (pinned ffmpeg@7 first).
    """
    current = shutil.which("ffmpeg")
    if current and _works(current):
        return os.path.dirname(current)
    for d in _CANDIDATE_DIRS:
        cand = os.path.join(d, "ffmpeg")
        if os.path.exists(cand) and _works(cand):
            return d
    return None


def ffmpeg_env(base_env: dict | None = None) -> tuple[dict, str | None]:
    """Return (env, ffmpeg_dir): a copy of the environment with a working ffmpeg
    prepended to PATH. ffmpeg_dir is None when nothing usable was found."""
    env = dict(base_env if base_env is not None else os.environ)
    d = resolve_ffmpeg_dir()
    if d:
        env["PATH"] = d + os.pathsep + env.get("PATH", "")
    return env, d


REMEDIATION = (
    "No working ffmpeg found. The system ffmpeg likely broke on a Homebrew upgrade "
    "(dylib ABI mismatch, e.g. ffmpeg 8 vs an upgraded x265). Fix the system one with "
    "`brew reinstall ffmpeg`, or install a pinned fallback: "
    "`brew install ffmpeg@7 && brew pin ffmpeg@7`."
)
