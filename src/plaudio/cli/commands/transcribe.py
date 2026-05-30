"""`plaudio transcribe AUDIO [--vocab FILE] [--language LANG] [--out DIR]`"""
from __future__ import annotations
import argparse, pathlib, sys
from plaudio.core.transcribe import transcribe, load_vocab_prompt, DEFAULT_MODEL


def cmd_transcribe(args: argparse.Namespace) -> int:
    audio = pathlib.Path(args.audio).expanduser()
    out_dir = pathlib.Path(args.out).expanduser() if args.out else audio.parent
    vocab = load_vocab_prompt(pathlib.Path(args.vocab).expanduser()) if args.vocab else ""
    try:
        segs, elapsed = transcribe(audio, out_dir=out_dir, language=args.language,
                                   vocab=vocab, model=args.model)
    except FileNotFoundError as e:
        print(f"audio not found: {e}", file=sys.stderr)
        return 2
    print(f"ok {len(segs)} segments in {elapsed:.1f}s "
          f"({len(segs)/max(elapsed,1e-3):.1f} seg/s)")
    print(f"  output: {out_dir / (audio.stem + '.json')}")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    t = sub.add_parser("transcribe", help="mlx-whisper ASR on an audio file")
    t.add_argument("audio")
    t.add_argument("--vocab", help="path to a vocab file (one term per line); default empty")
    t.add_argument("--language", default="en")
    t.add_argument("--out", help="output directory; default: same as audio")
    t.add_argument("--model", default=DEFAULT_MODEL)
    t.set_defaults(func=cmd_transcribe)
