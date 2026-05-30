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

    def enrol(
        self,
        *,
        name: str,
        embedding: list[float],
        enrolled_from: str,
        duration_s: float,
        n_speakers_in_audio: int,
        notes: str,
        embedding_model: str,
    ) -> VoiceProfile:
        profile = VoiceProfile(
            id=str(uuid.uuid4()),
            name=name,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=len(embedding),
            enrolled_from=enrolled_from,
            enrolled_at=datetime.datetime.utcnow().isoformat() + "Z",
            duration_s=duration_s,
            n_speakers_in_audio=n_speakers_in_audio,
            notes=notes,
        )
        self.profiles.append(profile)
        return profile

    def enrol_from_audio(
        self,
        audio_path: pathlib.Path,
        *,
        name: str,
        start_s: float | None,
        end_s: float | None,
        hf_token: str,
        notes: str = "",
        num_speakers: int | None = None,
    ) -> VoiceProfile:
        """Run pyannote diarisation, pick the SPEAKER_NN with maximum overlap in
        [start_s, end_s], use its mean embedding to enrol."""
        from plaudio.core.diarise import diarise_with_embeddings
        result = diarise_with_embeddings(audio_path, hf_token=hf_token, num_speakers=num_speakers)
        if not result.embeddings_by_label:
            raise RuntimeError("pyannote returned no speaker_embeddings")
        totals: dict[str, float] = {}
        for tstart, tend, sp in result.turns:
            if start_s is None or end_s is None:
                totals[sp] = totals.get(sp, 0.0) + (tend - tstart)
            else:
                ovl = max(0.0, min(tend, end_s) - max(tstart, start_s))
                if ovl > 0:
                    totals[sp] = totals.get(sp, 0.0) + ovl
        if not totals:
            raise RuntimeError(f"No speaker overlaps [{start_s}, {end_s}]")
        target_label = max(totals.items(), key=lambda kv: kv[1])[0]
        emb = result.embeddings_by_label[target_label]
        duration_s = (end_s - start_s) if (start_s is not None and end_s is not None) else totals[target_label]
        return self.enrol(
            name=name,
            embedding=emb,
            enrolled_from=str(audio_path),
            duration_s=float(duration_s),
            n_speakers_in_audio=len(result.embeddings_by_label),
            notes=notes,
            embedding_model="pyannote/speaker-diarization-3.1 (DiarizeOutput.speaker_embeddings)",
        )
