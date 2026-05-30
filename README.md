# Plaudio

**Voice-bank-first speaker labelling for the Plaud Note family. Local. macOS Apple Silicon.**

[![License: AGPL v3 or later](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform: macOS Apple Silicon](https://img.shields.io/badge/platform-macOS%20Apple%20Silicon-lightgrey.svg)]()
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

> Plaudio takes audio from your Plaud Note (or any recorder), transcribes it locally with mlx-whisper, identifies who said what by matching each speaker against your own voice bank, and stores everything in a searchable SQLite + FTS5 corpus. Your audio, your transcripts, your bank. No cloud round-trip.

## Why this exists

The standard local diarisation pipeline (pyannote-audio 3.1 in its default cluster-then-match mode) silently merges similar-pitched voices into one cluster. Put four people in their 30s with similar accents into a meeting, and the diariser will collapse them into `SPEAKER_04` and confidently label every utterance with the wrong owner.

Plaudio fixes this with **voice-bank-first sliding-window labelling**: slide a 2-second window across the audio, embed each window with `pyannote/embedding`, and cosine-match it against profiles you enrolled previously. Each window picks its own match independently, so similar voices get assigned to the right person instead of being merged. Unmatched windows stay as `Unknown` (you enrol them next time).

The other half of the package is operational: a CLI that does the boring parts (transcribe, label, search) and stores the result in a corpus you can query in your terminal.

```
$ plaudio db search "decision"
-- 2026-05-30 | Strategy review (M_2026-05-30-strat) --
  [12:34-12:42] Alice Smith: I think the decision is to ship by Friday.
  [13:01-13:06] Bob Jones: Agreed. Let me draft the comms.
```

## How it compares

| Tool | Local | Speaker labels | Voice bank | macOS-native | Plaud cloud sync |
|---|---|---|---|---|---|
| **Plaudio (this)** | yes | sliding voice-bank match | yes | mlx-whisper | v0.2 |
| whisperX | yes | pyannote cluster-then-match | no | CPU/CUDA | no |
| Riffado (formerly OpenPlaud) | yes (Docker) | none built-in | no | cross-platform | yes |
| Plaud cloud (default) | no | varies | per-recording manual labels only | n/a | yes |

The differentiator is the voice bank: enrol Alice once with a clean 30-second clip, and every future meeting auto-labels her by voice. Cluster-based pipelines redo speaker clustering from scratch on every recording.

## Scope, honestly

- **macOS on Apple Silicon only.** mlx-whisper is the ASR backend; it doesn't run on Linux or Intel Macs.
- **Plaud Note Pro family is the v0.1 target.** Plaud cloud sync arrives in v0.2.
- **Solo-maintained personal project.** Issues welcome. No SLAs, no roadmap promises beyond v0.2.

If you need cross-platform support, a web UI, or production-grade SLAs, this isn't your tool.

## Install

```bash
pip install plaudio
plaudio doctor
```

`plaudio doctor` checks ffmpeg, mlx-whisper, pyannote, the HuggingFace token (the diarisation model is gated, free, accept the agreement once), and torch MPS. It tells you exactly what to fix.

## Quickstart

```bash
# 1. enrol one voice (30 seconds of someone speaking alone, with their knowledge)
plaudio enrol alice-clean.mp3 --name "Alice Smith" --start 0 --end 30 --num-speakers 1

# 2. transcribe a meeting
plaudio transcribe meeting.mp3 --language en

# 3. convert Whisper output to Plaudio's transcript shape (see examples/quickstart.md)

# 4. label speakers from your bank
plaudio match meeting.mp3 meeting.plaud.json --threshold 0.55 --report

# 5. ingest into the searchable corpus
plaudio db ingest meeting.plaud.json \
  --meeting-id 2026-05-30-team \
  --date 2026-05-30 \
  --title "Team weekly"

# 6. search across every meeting you've ever ingested
plaudio db search "design decision"
plaudio db search "deadline" --speaker "Alice Smith"
```

See [`examples/quickstart.md`](examples/quickstart.md) for the full walkthrough.

## Interactive labelling: bootstrap once, label nothing forever

If you have used the Plaud app, you have done this dance: after every recording, you tap each speaker cluster, type a name, watch the labels propagate through the transcript, and repeat for the next meeting. The work is per-recording. Tomorrow's meeting starts at zero.

Plaudio inverts the cycle. `plaudio label` plays the same per-cluster prompt, but it adds an `--enrol` flag that writes the voice into your bank as you go. The next time the same person speaks in any recording, `plaudio match` labels them automatically. After ten or so meetings with your usual circle, you stop labelling entirely.

```bash
# Bootstrap mode: interactive playback + auto-enrolment in one pass
plaudio label meeting.mp3 meeting.plaud.json --enrol

# Batch mode: you already know who's who, skip the audio
plaudio label meeting.mp3 meeting.plaud.json \
    --batch-label "SPEAKER_00=Alice Smith,SPEAKER_01=Bob Jones" --enrol

# Re-enrol clusters that are already labelled correctly (bank update only)
plaudio label meeting.mp3 meeting.plaud.json --enrol-only
```

The interactive loop:

1. For each unknown cluster with ≥15s of airtime, find the longest clean monologue.
2. Slice it out with ffmpeg, play through `afplay` in the background.
3. Show the matching transcript text on screen.
4. Prompt: type a name, or `s`kip, or `u`nknown, or `r`eplay, or `q`uit.
5. Write the label to the JSON immediately (resumable on Ctrl-C).
6. With `--enrol`: use a wider 3-minute window (the cleanest 3 minutes of that speaker's airtime) to compute a robust embedding and add it to the voice bank.

This is the difference between a labelling tool and a learning tool. Plaud's app helps you for one recording. Plaudio's `label` helps you forever, because every label you type today is a profile that auto-matches tomorrow.

## Biometric data warning

`voicebank.json` contains voice fingerprints derived from real people. **Treat it like a password file.**

- Only enrol someone with their knowledge. Plaudio prints a reminder the first time you enrol.
- The bank lives at `~/Library/Application Support/plaudio/voicebank.json` with permissions `0600`. Plaudio never syncs it to any cloud.
- If you copy the bank to iCloud, Git, or S3, that's your decision and your responsibility.

## Subcommands

```
plaudio transcribe AUDIO [--vocab FILE] [--language LANG] [--out DIR]
plaudio match AUDIO TRANSCRIPT [--threshold T] [--report]
plaudio enrol AUDIO --name "Firstname Lastname" [--start S] [--end S]
plaudio label AUDIO TRANSCRIPT [--enrol] [--batch-label "L0=Name,L1=Name"]
plaudio clean TRANSCRIPT_MD [--corrections FILE]
plaudio db ingest|search|list ...
plaudio voicebank list|export|import|migrate|remove ...
plaudio plaud login|list|sync                 (v0.2; v0.1 prints a roadmap notice)
plaudio doctor
plaudio version
```

## Stack

mlx-whisper for on-device ASR (Apple's MLX framework, runs on the Neural Engine and GPU), pyannote-audio 3.1 for diarisation and the embedding model, SQLite + FTS5 trigram tokeniser for the corpus (trigram so Chinese-English code-switched search works), argparse for the CLI (no extra dependency), AGPL-3.0. Full rationale in [`STACK.md`](STACK.md).

## Roadmap

- **v0.1 (now):** library + CLI for the audio-in pipeline. macOS Apple Silicon only. Plaud cloud sync stubbed.
- **v0.2:** Plaud cloud sync (auth, list, download). Schema-stable voicebank migrate.
- **v0.3+:** depends on what users actually need. Open an issue to vote.

## License

AGPL-3.0-or-later. The full text is in [`LICENSE`](LICENSE).

Commercial license available on request. Open an issue tagged `license` and we can talk.

## Acknowledgements

- [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) for fast on-device ASR on Apple Silicon.
- [pyannote-audio](https://github.com/pyannote/pyannote-audio) for the gated 3.1 diarisation pipeline and the embedding model.
- [OpenAI Whisper](https://github.com/openai/whisper) for the ASR architecture.
- [Plaud](https://www.plaud.ai/) for the recorder hardware that started this project.

## Contributing

PRs welcome but read [`CONTRIBUTING.md`](CONTRIBUTING.md) first. There's a leak-audit on every commit (private wordlist scan + secret scan); the `--no-verify` bypass is forbidden. Use fabricated names in tests and examples.
