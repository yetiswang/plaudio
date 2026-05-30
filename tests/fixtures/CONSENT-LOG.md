<!-- tests/fixtures/CONSENT-LOG.md -->
# Fixture consent log

This directory holds audio fixtures used in opt-in integration tests
(`pytest -m integration`).

| File | Source | Licence | Consent | Date |
|---|---|---|---|---|
| `librivox-30s.wav` | LibriVox recording (URL TBD) | Public domain (US) | not applicable (public domain) | TBD |
| `self-30s.wav` | Recorded by repository author | Public-domain dedication for fixture use | Self-consent | TBD |

The repository ships without populated fixtures. To enable the integration
test, drop a 30-second WAV (16 kHz mono) at the paths above and update this
log with the actual source URLs and dates.
