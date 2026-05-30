"""Plaud cloud API client. Wraps the MCP token store for v0; standalone OAuth in v0.2."""
from __future__ import annotations
import json, pathlib

DEFAULT_TOKEN_PATH = pathlib.Path("~/.plaud/tokens-mcp.json").expanduser()


class TokenStore:
    def __init__(self, path: pathlib.Path = DEFAULT_TOKEN_PATH):
        self.path = pathlib.Path(path).expanduser()

    def access_token(self) -> str:
        if not self.path.exists():
            raise FileNotFoundError(
                f"Plaud token file not found at {self.path}. "
                f"Run the Plaud MCP login flow first (see README)."
            )
        data = json.loads(self.path.read_text())
        return data["access_token"]


class PlaudClient:
    def __init__(self, token_store: TokenStore | None = None):
        self.tokens = token_store or TokenStore()

    def list_recordings(self, *, since: str | None = None) -> list[dict]:
        """Stub: implement against Plaud's API in a follow-up. v0 returns []."""
        return []

    def presigned_url(self, file_id: str) -> str:
        raise NotImplementedError("Plaud cloud download lands in v0.2")
