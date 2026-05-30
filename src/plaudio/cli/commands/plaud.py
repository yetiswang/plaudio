"""`plaudio plaud login|list|sync` -- stubs in v0.1, full impl in v0.2."""
from __future__ import annotations
import argparse

V02_MSG = (
    "Plaud cloud sync is not implemented in v0.1. See README -> Roadmap. "
    "For now: use the Plaud MCP via your editor's MCP host, or the Plaud "
    "mobile app, then point `plaudio transcribe` at the downloaded audio."
)


def cmd_stub(args: argparse.Namespace) -> int:
    print(V02_MSG)
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("plaud", help="Plaud cloud sync (v0.2)")
    psub = p.add_subparsers(dest="plaud_cmd", required=True)
    psub.add_parser("login").set_defaults(func=cmd_stub)
    psub.add_parser("list").set_defaults(func=cmd_stub)
    psub.add_parser("sync").set_defaults(func=cmd_stub)
