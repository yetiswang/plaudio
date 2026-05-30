"""argparse dispatcher. Subcommands attach in cli/commands/*."""
from __future__ import annotations
import argparse, sys
from plaudio import __version__
from plaudio.cli.commands import voicebank as cmd_voicebank

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="plaudio", description="Voice-bank-first speaker labelling.")
    p.add_argument("-V", "--version", action="version", version=f"plaudio {__version__}")
    sub = p.add_subparsers(dest="cmd", required=False)
    sub.add_parser("version", help="print version and exit")
    cmd_voicebank.register(sub)
    return p

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "version" or args.cmd is None:
        print(f"plaudio {__version__}")
        return 0
    if hasattr(args, "func"):
        return args.func(args)
    parser.error(f"unknown command: {args.cmd}")
    return 2
