# Contributing

## Bug reports

Open an issue with: macOS version, Python version, `plaudio doctor` output, the exact command that failed, and the last 20 lines of stderr.

## Pull requests

Plaudio runs an automated audit on every commit and CI build. The audit scans the diff against a private wordlist of personal terms maintained by the maintainer. **You can't see the wordlist; just don't include personal data of real people in commits.**

Specifically:

- Use fabricated names in examples and tests. `Alice Smith`, `Bob Jones`, and similar.
- Don't add real recordings to `tests/fixtures/` without an entry in `tests/fixtures/CONSENT-LOG.md`.
- Don't put real meeting topics in commit messages or docstrings.

The pre-commit hook is mandatory. **Never** use `git commit --no-verify` on this repo. If a legitimate term trips the audit, add a line to `audit-allowed-terms.txt` with a justification comment.

## Tests

`pytest` from the repo root runs unit tests. Add `-m integration` to opt into the end-to-end test (requires fixtures, see `tests/fixtures/CONSENT-LOG.md`).

TDD is expected for new features. Write the failing test, then the implementation, then commit.

## Code style

- Python >= 3.11.
- ruff for linting (`ruff check .`).
- 100-column lines.
- Type hints on public functions.
- No em-dashes in prose (commas, periods, parens, colons).

## Scope

Plaudio is intentionally narrow: macOS, Apple Silicon, Plaud Note family. PRs that broaden the platform surface (Linux support, alternative ASR backends, web UI) need a design discussion first. Open an issue tagged `scope` before coding.
