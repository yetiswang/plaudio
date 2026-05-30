# Plaudio stack

Why each piece was chosen and what would force a swap.

## ASR: mlx-whisper

[mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) wraps OpenAI's Whisper model with Apple's MLX framework. On Apple Silicon it runs the encoder/decoder on the unified-memory GPU and Neural Engine.

**Why**:

- 6× realtime on a base M-series chip (measured against Whisper Large v3) without any quantisation tricks.
- The CLI accepts an `--initial-prompt` flag, which is exactly the vocab-anchoring mechanism Plaudio uses.
- Drop-in: `mlx_whisper audio.mp3 --output-format json` produces the segment shape we need.

**What would force a swap**:

- If MLX-side maintenance lapsed for ≥6 months. Fallback: `faster-whisper` via CTranslate2, with the CPU/CUDA branches gated behind a backend abstraction (a v0.3 conversation).
- A new ASR family that materially beats Whisper Large v3 on Dutch + English + technical vocabulary. Currently none does at this latency/cost.

## Diarisation + embeddings: pyannote-audio 3.1

[pyannote-audio](https://github.com/pyannote/pyannote-audio) 3.1's `pyannote/speaker-diarization-3.1` pipeline produces speaker turns and per-cluster mean embeddings in one shot. The same package exposes `pyannote/embedding` as a sliding-window embedder for Plaudio's voice-bank matcher.

**Why**:

- The de facto open-source standard for offline diarisation. Active maintenance, broad benchmarks, MPS-compatible on Apple Silicon (via torch).
- `DiarizeOutput.speaker_embeddings` gives per-speaker mean embeddings without a separate model call. One gated download covers both clustering and embeddings.
- The 256-dim embedding has good discriminative power across same-language speakers in real meeting conditions.

**What would force a swap**:

- A faster Apple Silicon-native diariser (someone is doing pyannote-on-MLX work, watch that space).
- A gated-model change that makes the HuggingFace acceptance flow worse than it already is.

**Workaround we ship**: pyannote 4.x defaults to `torchcodec` for audio loading. Torchcodec wants libavutil 56/57 (ffmpeg 4/5). Homebrew ships ffmpeg 7+ (libavutil 59+). We sidestep by pre-converting audio to 16 kHz mono WAV via ffmpeg, then loading with `soundfile`, then passing `{waveform, sample_rate}` to the pyannote pipeline. Documented in `src/plaudio/core/diarise.py`.

## Corpus: SQLite + FTS5 (trigram tokenizer)

The transcripts corpus is a single-file SQLite database at `~/Library/Application Support/plaudio/transcripts.db`, with an FTS5 virtual table over `segments` content using the **trigram** tokenizer.

**Why SQLite at all**:

- Single-file, zero-server, runs everywhere Python runs.
- Concurrency for a single user is fine; we don't need PostgreSQL.
- FTS5 is shipped in Python's `sqlite3` module on macOS by default. No external dependency.

**Why trigram (not unicode61)**:

- The default `unicode61` tokenizer treats CJK characters as a single token glued to adjacent Latin words. A segment like `让我看看这个 nanolab 的人` becomes tokenized in a way that searching for "nanolab" misses the segment.
- The `trigram` tokenizer breaks every text into overlapping 3-character grams. This handles ZH+EN code-switching cleanly. The price is a 3-character minimum query length, which is fine for a search command.

**What would force a swap**:

- A real need for multi-process concurrent writes (then Postgres + tsvector).
- A scale jump past tens of thousands of meetings (then a tantivy or Meilisearch backend).

## CLI: argparse (standard library)

The CLI uses `argparse` with a dispatcher in `cli/main.py` and per-command modules in `cli/commands/`.

**Why argparse over click / typer**:

- Zero extra dependency. Plaudio's import surface stays small.
- argparse is enough for the surface we have (10 subcommands, no fancy callbacks).
- Subcommand modules can register themselves via a uniform `register(sub: argparse._SubParsersAction)` function. The dispatcher just calls `args.func(args)`.

**What would force a swap**:

- Rich shell completion across subcommands becoming a priority.
- Sub-sub-sub-command nesting beyond two levels.

## Voice bank: plain JSON, mode 0600

The voicebank is a single JSON file with an array of profile entries. Each profile has an embedding vector, a name, an enrolment timestamp, and a few audit fields. Multi-sample per name is intentional and the sliding matcher averages them.

**Why JSON**:

- Human-readable. Easy to inspect, export, copy between machines.
- No schema migration framework needed at v0.1 (we have one field, `schema_version`).
- Mode 0600 is enforced on every save.

**What would force a swap**:

- Banks growing past a few hundred profiles (then SQLite or a binary format).
- Need for encrypted-at-rest (then GPG-wrapped JSON or sqlite + sqlcipher).

## License: AGPL-3.0-or-later

**Why AGPL**:

- Keeps the option of a future dual-license open. As the original author, the maintainer can sell commercial exceptions to parties that don't want AGPL obligations.
- Forces forks that operate as a network service to share their source. The bar is reasonable for a project of this size and stops a SaaS-wrapping fork from quietly extracting all the value.

**Why not MIT**:

- MIT closes the commercial-pivot path (once code is MIT, you can't sell exclusive rights). Plaudio is intentionally keeping that option open.

**What would change this**:

- A clear signal from contributors that AGPL is a barrier to adoption. Most likely path is dual-licensing rather than relicensing.

## Audit toolchain: vendored `plaudio_audit` micro-package

Every commit and CI build runs against a private wordlist of personal terms (colleague surnames, project codes, etc.) maintained by the maintainer. The scanner (`plaudio_audit.wordlist.scan`) is word-boundary case-insensitive matching; an `audit-allowed-terms.txt` file in the repo provides per-term overrides with justifications.

**Why a separate package**:

- The wordlist scanner has zero runtime cost to Plaudio users (they don't install `plaudio_audit`).
- The pre-commit hook just pipes `git diff --cached -U0` into `python3.13 -m plaudio_audit.precommit`.
- CI duplicates the check.

**What would change this**:

- If the project moves to a multi-maintainer model, the audit moves to a per-PR review process (and the wordlist becomes a community concern, which is a much bigger conversation).

## Test toolchain: pytest, no fixtures of real audio

Pytest with one mandatory marker (`integration`, opt-in). No real meeting audio in the repo. All test data is synthetic embeddings, fabricated names (Alice Smith, Bob Jones), and a stub `.plaud.json` shape.

**Why no real audio**:

- A real meeting recording in `tests/fixtures/` would either leak voices or require a consent log that doesn't scale.
- The unit tests verify algorithms (cosine, coalesce_runs, FTS5 trigram), not the speech models themselves.
- The opt-in integration test uses a LibriVox public-domain clip plus a self-recorded clip with a documented consent log.

## What's NOT in the stack

- **No web UI.** Riffado already covers that surface; Plaudio is a terminal tool.
- **No Docker.** macOS-only means we lean on the system Python + Homebrew, not containers.
- **No background daemon.** Every Plaudio invocation is a discrete CLI call. State is on disk.
- **No telemetry.** Plaudio never phones home. The maintainer doesn't know how many people use it.
