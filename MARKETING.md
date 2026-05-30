# Marketing copy for the Plaudio v0.1.0 launch

Ready-to-post copy for the platforms Plaudio's likely audience hangs out on. Pick what fits. Each variant is calibrated to the platform's tone and length norms. None of them oversell what v0.1 actually does.

---

## Show HN (Hacker News submission)

**Title** (80 chars max, no emoji per HN norms):

```
Show HN: Plaudio – voice-bank-first speaker labelling for the Plaud Note (macOS)
```

**Body** (first comment, ~150 words):

```
Plaudio is a small Python package I built to solve one specific problem with
pyannote-audio's default diarisation: when four people with similar voices are
in a meeting, the cluster-based labeller silently merges them into one
SPEAKER cluster and confidently attributes everything to the wrong people.

The fix is voice-bank-first sliding-window labelling. You enrol each colleague
once with a 30-second clean clip. From then on, every recording gets labelled
by sliding a 2s window across the audio, embedding each window, and
cosine-matching against your bank. Each window picks its match independently,
so similar voices don't get merged.

Stack: mlx-whisper for ASR (Apple Silicon only), pyannote-3.1 for the
embedding model, SQLite + FTS5 trigram for the searchable transcript corpus,
argparse for the CLI. AGPL-3.0.

Scope is intentionally narrow: macOS Apple Silicon + Plaud Note Pro family.
No Linux, no Docker, no cloud. v0.2 will add Plaud cloud sync.

Repo: https://github.com/yetiswang/plaudio
```

---

## X / Twitter / Mastodon thread

**Tweet 1** (280):

```
Shipped Plaudio v0.1.0: voice-bank-first speaker labelling for the Plaud Note family.

The problem: pyannote merges similar voices into one cluster.

The fix: enrol each voice once. Slide a 2s window. Match per-window. No merging.

macOS Apple Silicon, AGPL.

https://github.com/yetiswang/plaudio
```

**Tweet 2** (280):

```
Stack:
- mlx-whisper for ASR (6× realtime on M-series)
- pyannote-3.1 for the embedding model
- SQLite + FTS5 trigram tokenizer for the corpus (handles ZH+EN code-switching)
- argparse for the CLI

Single pip install. No Docker, no cloud round-trip, no telemetry.
```

**Tweet 3** (280):

```
v0.1 is the audio-in pipeline:

plaudio enrol clip.mp3 --name "Alice"
plaudio transcribe meeting.mp3
plaudio match meeting.mp3 meeting.plaud.json
plaudio db ingest meeting.plaud.json --meeting-id ...
plaudio db search "deadline" --speaker "Alice"

v0.2 adds Plaud cloud sync. Issues/PRs welcome.
```

---

## LinkedIn (longer-form, professional register)

```
Shipping a small open-source tool today: Plaudio, voice-bank-first speaker
labelling for the Plaud Note voice recorder family. AGPL-3.0, macOS Apple
Silicon, single pip install.

The core problem it solves: cluster-based speaker diarisation
(the standard approach) silently merges similar-pitched voices into one
cluster. If you record a meeting with four colleagues who happen to have
similar accents and registers, you get confident-but-wrong attribution
everywhere.

Plaudio takes a different approach. You enrol each voice once with a clean
30-second clip. From then on, the pipeline slides a 2-second window across
your meeting audio, embeds each window with pyannote/embedding, and
cosine-matches against your enrolled profiles independently. Similar voices
get assigned to the right person instead of being merged. Unmatched windows
stay as Unknown until you enrol that speaker too.

Built on the Apple ML stack: mlx-whisper for fast on-device ASR, pyannote-3.1
for the embedding model, SQLite + FTS5 with a trigram tokenizer so Chinese-
English code-switched search works out of the box.

The whole pipeline is local. No telemetry, no cloud round-trip, no Docker.

Repo and full readme: https://github.com/yetiswang/plaudio

Open to feedback, PRs, and bug reports. The roadmap is honest: v0.2 will add
Plaud cloud sync; v0.3+ depends on what early users actually need.
```

---

## Reddit r/MacApps

**Title:**

```
[Tool] Plaudio: local voice-bank-first speaker labelling for Plaud Note recorders (macOS only)
```

**Body:**

```
Built this for myself, sharing in case it's useful to anyone else who
records meetings with a Plaud Note.

Plaudio runs the entire transcription + speaker-labelling pipeline locally
on Apple Silicon: mlx-whisper for ASR, pyannote-3.1 for diarisation, and a
voice-bank-first sliding matcher that fixes the "four similar voices get
merged into one SPEAKER" problem you get from default pyannote.

The workflow:

1. Enrol each frequent speaker once with a 30-second clean clip.
2. Run `plaudio transcribe + match` on a new meeting.
3. Ingest into a SQLite+FTS5 corpus.
4. Search across every meeting you've ever recorded.

Single `pip install plaudio` if you have Python 3.11+ on an M-series Mac.

AGPL-3.0, single-maintainer project. Scope is intentionally narrow (no
Linux, no Windows, no Docker). Plaud cloud sync arrives in v0.2.

Repo: https://github.com/yetiswang/plaudio
```

---

## Reddit r/Python

**Title:**

```
Plaudio: voice-bank-first speaker labelling for the Plaud Note recorder family. mlx-whisper + pyannote + SQLite/FTS5
```

**Body:**

```
Small new package up on PyPI: `pip install plaudio`. macOS Apple Silicon
only.

Solves a specific problem: pyannote-audio's default cluster-based diarisation
merges similar-pitched voices into one cluster. Plaudio bypasses that with
sliding-window voice-bank matching (slide a 2s window, embed each window,
cosine-match against profiles you enrolled previously).

Some choices I'm interested in feedback on:

- `argparse` for the CLI instead of click/typer (zero extra deps; the
  subcommand-register pattern stays tidy).
- `tokenize='trigram'` for the FTS5 transcripts corpus instead of unicode61
  (handles ZH+EN code-switched text cleanly; the 3-char minimum is a fine
  trade for a search command).
- Vendored `plaudio_audit` micro-package for the leak-audit pre-commit hook
  (one purpose, no runtime cost to Plaudio users).
- AGPL-3.0 to keep a future dual-license commercial path open.

Repo: https://github.com/yetiswang/plaudio
Stack rationale: https://github.com/yetiswang/plaudio/blob/main/STACK.md
```

---

## Hacker News / Lobste.rs short comment (when someone else posts a related thread)

```
We use a voice-bank-first sliding-window matcher in [Plaudio][1] to avoid
the cluster-merge failure mode. Enrol each speaker once, slide a 2s window
across the audio, cosine-match against the bank per window. Each window
picks its match independently, so similar voices don't get collapsed into a
single SPEAKER cluster. macOS Apple Silicon only for v0.1.

[1]: https://github.com/yetiswang/plaudio
```

---

## GitHub repo description (one-liner)

```
Voice-bank-first speaker labelling for the Plaud Note family. Local, macOS Apple Silicon, AGPL-3.0.
```

## GitHub topic tags

```
plaud, plaud-note, diarisation, speaker-identification, speaker-diarization,
whisper, mlx, mlx-whisper, pyannote, voice-recognition, transcription,
fts5, sqlite, agpl, macos, apple-silicon
```

---

## Asciinema demo script (optional, for the README later)

```
$ plaudio doctor
Plaudio doctor — environment check
  ok macOS: 14.5
  ok Apple Silicon: arm64
  ok Python: 3.13.12
  ok ffmpeg: /opt/homebrew/bin/ffmpeg
  ok mlx_whisper: ~/.local/bin/mlx_whisper
  ok pyannote.audio: 3.1.1
  ok HF token: ~/.huggingface/token
  ok torch MPS: available
Doctor: all checks passed.

$ plaudio enrol alice-30s.wav --name "Alice Smith" --start 0 --end 30 --num-speakers 1
plaudio enrol: enrolling a person's voice creates a biometric profile.
Only enrol with the speaker's knowledge.
enrolled Alice Smith (dim=256, duration=30s)
voicebank: ~/Library/Application Support/plaudio/voicebank.json

$ plaudio transcribe meeting.mp3 --language en
ok 47 segments in 62.4s (0.8 seg/s)
  output: meeting.json

$ plaudio match meeting.mp3 meeting.plaud.json --threshold 0.55 --report
  31 / 47 windows matched at threshold 0.55
  coalesced into 8 runs, relabelled 42 segments
Per-speaker durations:
  Alice Smith: 412s (6.9min)
  Bob Jones: 281s (4.7min)
  Unknown: 67s (1.1min)

$ plaudio db ingest meeting.plaud.json --meeting-id team-2026-05-30 --date 2026-05-30 --title "Team weekly"
ingested meeting 'team-2026-05-30'

$ plaudio db search "deadline" --speaker "Alice Smith"
-- 2026-05-30 | Team weekly (team-2026-05-30) --
  [12:34-12:42] Alice Smith: I think the deadline for the audit is end of week.
```

---

## Notes on use

- Pick **one** primary launch venue first, see if it draws any attention, then ladder out. Posting on five platforms at once for a niche tool just spreads thin.
- The Hacker News post is the highest-leverage shot if you want a wider engineering audience.
- The Reddit r/MacApps post is the right venue if you want users (not necessarily devs).
- The LinkedIn post is the safest for adjacent-professional reach without context-collapse risk.
- Save the X/Mastodon thread for after the first launch venue has a result to point at ("Show HN was discussed here:").
