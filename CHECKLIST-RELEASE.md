# Release checklist

Tick every box in the release PR before tagging `vX.Y.Z`. The CI gate runs the automated checks; this checklist covers the manual ones.

## Audit

- [ ] Private wordlist regenerated within the last 24h.
- [ ] CI audit job is green on the release commit.
- [ ] Wheel inspected manually (`unzip -l dist/*.whl`); no unexpected files.
- [ ] Wheel content greppped against the wordlist; zero hits.
- [ ] README scanned by eye for any reference to real people, projects, or organisations not on the public allow-list.
- [ ] Example data still uses fabricated names (Alice Smith, Bob Jones, etc.).
- [ ] No new test fixtures added without a `CONSENT-LOG.md` entry.

## Schema / compatibility

- [ ] `voicebank.json` schema_version unchanged, OR a `plaudio voicebank migrate` path is tested.
- [ ] Public API didn't break (no removed CLI subcommands, no required new args on existing ones).

## Post-publish

- [ ] Wait 5 minutes after `twine upload`, then `pip download plaudio==X.Y.Z` and re-grep against the wordlist.
- [ ] If a leak slipped through: yank the release immediately (`pypi yank`), open a hotfix tag.
