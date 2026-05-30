# Plaudio

**Voice-bank-first speaker labelling for the Plaud Note family. Local. macOS Apple Silicon.**

> **Scope statement.** macOS on Apple Silicon only. mlx-whisper for ASR, pyannote-audio 3.1 for diarisation. No Linux, no Windows, no Docker, no cloud transcription. If you're not on a Mac with an M-series chip, this isn't for you yet.

Plaudio takes an audio file, transcribes it locally, identifies who said what by matching each speaker against a small voice bank you build yourself, and stores the result in a searchable SQLite + FTS5 corpus. The novel part is **voice-bank-first sliding-window labelling**: instead of clustering speakers and matching the cluster to a profile (which silently merges similar voices), Plaudio slides a 2-second window across the audio, embeds each window, and cosine-matches against your enrolled voices independently. This eliminates the 4+ similar-voice merger failure mode that hits cluster-based diarisers.

## Install

```bash
pip install plaudio
plaudio doctor
```

`plaudio doctor` will tell you what's missing (ffmpeg, mlx-whisper, a HuggingFace token for the gated pyannote model, etc.) and how to install it.

## Quickstart

```bash
# 1. enrol one voice with a 30-second clean clip
plaudio enrol alice.mp3 --name "Alice Smith" --start 12 --end 42

# 2. transcribe a meeting
plaudio transcribe meeting.mp3

# 3. produce a Plaud-shape JSON (or convert from your own pipeline)
# (see examples/quickstart.md for the json shape)

# 4. label speakers from the voice bank
plaudio match meeting.mp3 meeting.plaud.json --threshold 0.55 --report

# 5. ingest into the searchable corpus
plaudio db ingest meeting.plaud.json \
  --meeting-id 2026-05-30-team \
  --date 2026-05-30 \
  --title "Team weekly"

# 6. search across all ingested meetings
plaudio db search "design decision"
plaudio db search "deadline" --speaker "Alice Smith"
```

## Biometric data warning

Your voicebank.json contains voice fingerprints derived from real people. **Treat it like a password file.**

- Only enrol someone with their knowledge. Plaudio prints a reminder on first enrolment.
- The bank lives at `~/Library/Application Support/plaudio/voicebank.json` with permissions `0600`. Plaudio never syncs it to any cloud.
- If you copy the bank to iCloud, Git, S3, or anywhere else, that's your call and your responsibility.

## Subcommands

```
plaudio transcribe AUDIO [--vocab FILE] [--language LANG] [--out DIR]
plaudio match AUDIO TRANSCRIPT [--threshold T] [--report]
plaudio enrol AUDIO --name "Firstname Lastname" [--start S] [--end S]
plaudio label AUDIO TRANSCRIPT [--enrol] [--batch-label "L0=Name,L1=Name"]
plaudio clean TRANSCRIPT_MD [--corrections FILE]
plaudio db ingest|search|list ...
plaudio voicebank list|export|import|migrate|remove ...
plaudio plaud login|list|sync         (v0.2; v0.1 prints a roadmap notice)
plaudio doctor
plaudio version
```

## Roadmap

- **v0.1** (now): library + Plaud-app stubs. macOS Apple Silicon only.
- **v0.2**: Plaud cloud sync (OAuth, list, download).
- **v0.3+**: depends on what users actually need.

## License

AGPL-3.0-or-later. Commercial license available on request: open an issue tagged `license`.

## Acknowledgements

- [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) for fast on-device ASR.
- [pyannote-audio](https://github.com/pyannote/pyannote-audio) for the embedding model and the gated diarisation pipeline.
- OpenAI's Whisper for the ASR foundation.
- Plaud for the recorder hardware that started this.
