"""Voice bank: per-name speaker embedding store.

Schema v1: a list of VoiceProfile entries. Multiple entries can share a name
(intentional: SlidingMatcher averages by name to build a robust mean embedding).

On disk: ~/Library/Application Support/plaudio/voicebank.json by default.
File mode forced to 0600 on every save (biometric data).
"""
from __future__ import annotations
import dataclasses, datetime, json, os, pathlib, uuid

SCHEMA_VERSION = 1

@dataclasses.dataclass
class VoiceProfile:
    id: str
    name: str
    embedding: list[float]
    embedding_model: str
    embedding_dim: int
    enrolled_from: str
    enrolled_at: str
    duration_s: float
    n_speakers_in_audio: int
    notes: str = ""

@dataclasses.dataclass
class VoiceBank:
    schema_version: int
    created_at: str
    model: str
    profiles: list[VoiceProfile]

    @classmethod
    def default_path(cls) -> pathlib.Path:
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            return pathlib.Path(xdg).expanduser() / "plaudio" / "voicebank.json"
        return pathlib.Path("~/Library/Application Support/plaudio/voicebank.json").expanduser()

    @classmethod
    def load(cls, path: pathlib.Path) -> "VoiceBank":
        if not path.exists():
            return cls(
                schema_version=SCHEMA_VERSION,
                created_at=datetime.datetime.utcnow().isoformat() + "Z",
                model="pyannote/speaker-diarization-3.1",
                profiles=[],
            )
        raw = json.loads(path.read_text())
        sv = raw.get("schema_version")
        if sv != SCHEMA_VERSION:
            raise ValueError(
                f"voicebank schema_version={sv}; this Plaudio supports only {SCHEMA_VERSION}. "
                f"Run `plaudio voicebank migrate` if upgrading."
            )
        profiles = [VoiceProfile(**p) for p in raw.get("profiles", [])]
        return cls(
            schema_version=sv,
            created_at=raw.get("created_at", ""),
            model=raw.get("model", ""),
            profiles=profiles,
        )

    def save(self, path: pathlib.Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "model": self.model,
            "profiles": [dataclasses.asdict(p) for p in self.profiles],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        os.chmod(path, 0o600)

    def by_name(self) -> dict[str, list[list[float]]]:
        """Group profile embeddings by name (used by SlidingMatcher to average)."""
        out: dict[str, list[list[float]]] = {}
        for p in self.profiles:
            out.setdefault(p.name, []).append(p.embedding)
        return out

    def remove(self, name: str) -> int:
        before = len(self.profiles)
        self.profiles = [p for p in self.profiles if p.name != name]
        return before - len(self.profiles)
