"""`plaudio voicebank ...` subcommands."""
from __future__ import annotations
import argparse, json, os, pathlib, shutil, sys
from plaudio.core.voicebank import VoiceBank

LEGACY_PATH = pathlib.Path("~/.local/share/vault-watcher/plaud-voice-profiles.json").expanduser()

def _bank_path() -> pathlib.Path:
    override = os.environ.get("PLAUDIO_VOICEBANK")
    if override:
        return pathlib.Path(override).expanduser()
    return VoiceBank.default_path()

def cmd_list(args: argparse.Namespace) -> int:
    bank = VoiceBank.load(_bank_path())
    if not bank.profiles:
        print("(voicebank empty)")
        return 0
    grouped = bank.by_name()
    print(f"{len(bank.profiles)} samples across {len(grouped)} people:")
    for name in sorted(grouped):
        s = len(grouped[name])
        print(f"  - {name} ({s} sample{'s' if s>1 else ''})")
    return 0

def cmd_export(args: argparse.Namespace) -> int:
    src = _bank_path()
    if not src.exists():
        print(f"voicebank not found at {src}", file=sys.stderr)
        return 2
    shutil.copy2(src, pathlib.Path(args.out_path).expanduser())
    print(f"exported {src} -> {args.out_path}")
    return 0

def cmd_import(args: argparse.Namespace) -> int:
    src = pathlib.Path(args.in_path).expanduser()
    if not src.exists():
        print(f"input not found: {src}", file=sys.stderr)
        return 2
    incoming = VoiceBank.load(src)
    bank = VoiceBank.load(_bank_path())
    existing = {p.id for p in bank.profiles}
    added = 0
    for p in incoming.profiles:
        if p.id in existing:
            continue
        bank.profiles.append(p)
        added += 1
    bank.save(_bank_path())
    print(f"imported {added} new profile(s)")
    return 0

def cmd_migrate(args: argparse.Namespace) -> int:
    if not LEGACY_PATH.exists():
        print(f"(no legacy file at {LEGACY_PATH})")
        return 0
    raw = json.loads(LEGACY_PATH.read_text())
    legacy_profiles = raw.get("profiles", [])
    if not legacy_profiles:
        print("(legacy file empty)")
        return 0
    bank = VoiceBank.load(_bank_path())
    for old in legacy_profiles:
        bank.enrol(
            name=old["name"],
            embedding=old["embedding"],
            enrolled_from=old.get("enrolled_from", "legacy"),
            duration_s=float(old.get("end_s") or 0) - float(old.get("start_s") or 0),
            n_speakers_in_audio=int(old.get("n_speakers_in_audio") or 1),
            notes=f"migrated from legacy: {old.get('notes','')}",
            embedding_model=old.get("model", "pyannote/speaker-diarization-3.1"),
        )
    bank.save(_bank_path())
    print(f"migrated {len(legacy_profiles)} profile(s) from {LEGACY_PATH} -> {_bank_path()}")
    return 0

def cmd_remove(args: argparse.Namespace) -> int:
    bank = VoiceBank.load(_bank_path())
    n = bank.remove(args.name)
    bank.save(_bank_path())
    print(f"removed {n} profile(s) for {args.name!r}")
    return 0

def register(sub: argparse._SubParsersAction) -> None:
    vb = sub.add_parser("voicebank", help="manage the voice bank")
    vbsub = vb.add_subparsers(dest="vb_cmd", required=True)
    vbsub.add_parser("list").set_defaults(func=cmd_list)
    e = vbsub.add_parser("export"); e.add_argument("out_path"); e.set_defaults(func=cmd_export)
    i = vbsub.add_parser("import"); i.add_argument("in_path"); i.set_defaults(func=cmd_import)
    vbsub.add_parser("migrate").set_defaults(func=cmd_migrate)
    r = vbsub.add_parser("remove"); r.add_argument("--name", required=True); r.set_defaults(func=cmd_remove)
