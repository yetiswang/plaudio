"""`plaudio enrol AUDIO --name X --start S --end S`"""
from __future__ import annotations
import argparse, os, pathlib, sys
from plaudio.core.voicebank import VoiceBank

DEFAULT_TOKEN_FILE = pathlib.Path("~/.huggingface/token").expanduser()

CONSENT_TEXT = """\
plaudio enrol: enrolling a person's voice creates a biometric profile.
Only enrol with the speaker's knowledge. The voicebank lives at
{path} (mode 0600); back it up explicitly if you want it elsewhere.
"""

def _bank_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("PLAUDIO_VOICEBANK", str(VoiceBank.default_path()))).expanduser()

def cmd_enrol(args: argparse.Namespace) -> int:
    bank_path = _bank_path()
    if not bank_path.exists():
        print(CONSENT_TEXT.format(path=bank_path), file=sys.stderr)
    token_file = pathlib.Path(args.hf_token_file).expanduser()
    if not token_file.exists():
        print(f"HF token not found at {token_file}; create it or pass --hf-token-file.", file=sys.stderr)
        return 2
    hf_token = token_file.read_text().strip()
    bank = VoiceBank.load(bank_path)
    audio = pathlib.Path(args.audio).expanduser()
    try:
        profile = bank.enrol_from_audio(
            audio,
            name=args.name,
            start_s=args.start,
            end_s=args.end,
            hf_token=hf_token,
            notes=args.notes,
            num_speakers=args.num_speakers,
        )
    except Exception as e:
        print(f"enrolment failed: {e}", file=sys.stderr)
        return 1
    bank.save(bank_path)
    print(f"enrolled {profile.name} (dim={profile.embedding_dim}, duration={profile.duration_s:.0f}s)")
    print(f"voicebank: {bank_path}")
    return 0

def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("enrol", help="enrol a voice profile from audio")
    p.add_argument("audio")
    p.add_argument("--name", required=True)
    p.add_argument("--start", type=float, default=None, help="start (sec) of the clean window")
    p.add_argument("--end", type=float, default=None, help="end (sec) of the clean window")
    p.add_argument("--num-speakers", type=int, default=None,
                   help="hint to pyannote; helps when the audio has few speakers")
    p.add_argument("--notes", default="")
    p.add_argument("--hf-token-file", default=str(DEFAULT_TOKEN_FILE))
    p.set_defaults(func=cmd_enrol)
