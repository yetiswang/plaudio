"""`plaudio match AUDIO TRANSCRIPT [--threshold T] [--report]`"""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import sys
from plaudio.core.voicebank import VoiceBank
from plaudio.core.slidingmatch import SlidingMatcher, DEFAULT_THRESHOLD


def _bank_path() -> pathlib.Path:
    return pathlib.Path(
        os.environ.get("PLAUDIO_VOICEBANK", str(VoiceBank.default_path()))
    ).expanduser()


def cmd_match(args: argparse.Namespace) -> int:
    audio = pathlib.Path(args.audio).expanduser()
    jpath = pathlib.Path(args.transcript).expanduser()
    if not audio.exists():
        print(f"audio not found: {audio}", file=sys.stderr)
        return 2
    if not jpath.exists():
        print(f"transcript not found: {jpath}", file=sys.stderr)
        return 2
    bank = VoiceBank.load(_bank_path())
    matcher = SlidingMatcher(bank, threshold=args.threshold)
    data = json.loads(jpath.read_text())
    segs = data.get("segments", [])
    report = matcher.label_segments(audio, segs)
    jpath.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(
        f"  {report.get('n_matched', 0)} / {report.get('n_total', 0)} windows matched"
        f" at threshold {args.threshold}"
    )
    print(
        f"  coalesced into {report.get('n_runs', 0)} runs,"
        f" relabelled {report.get('n_segments_relabelled', 0)} segments"
    )
    if args.report:
        from collections import defaultdict

        durs: dict[str, float] = defaultdict(float)
        for s in segs:
            durs[s["speaker"]] += (s["end_time"] - s["start_time"]) / 1000.0
        print("\nPer-speaker durations:")
        for k, v in sorted(durs.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v:.0f}s ({v/60:.1f}min)")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("match", help="re-label transcript via voice-bank sliding match")
    p.add_argument("audio")
    p.add_argument("transcript")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    p.add_argument("--report", action="store_true")
    p.set_defaults(func=cmd_match)
