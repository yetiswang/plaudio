# Plaudio quickstart

Five steps from a fresh install to searchable transcripts.

## 0. Install and verify

```bash
pip install plaudio
plaudio doctor
```

If doctor reports failures, fix them before continuing.

## 1. Enrol a voice

You need a ~30-second clip of one person speaking alone. Tell them you're going to record their voice for the bank.

```bash
plaudio enrol alice-clean-clip.mp3 --name "Alice Smith" --start 0 --end 30 --num-speakers 1
```

The `--num-speakers 1` hint helps pyannote when the audio really only has one speaker.

## 2. Transcribe a meeting

```bash
plaudio transcribe team-meeting.mp3 --language en
```

This produces `team-meeting.json` (raw Whisper output).

## 3. Convert to Plaudio's transcript shape

Plaudio's `.plaud.json` shape is:

```json
{
  "meta": {"language": "en", "n_speakers": 3},
  "segments": [
    {"start_time": 0, "end_time": 2000, "speaker": "Speaker 1", "content": "hello"},
    ...
  ]
}
```

For now you produce this yourself (a short Python script that converts Whisper segments). Full pipeline integration arrives later.

## 4. Label speakers from the voice bank

```bash
plaudio match team-meeting.mp3 team-meeting.plaud.json --threshold 0.55 --report
```

The report shows per-speaker airtime after labelling. Anyone not in the bank stays as `Unknown`; enrol them next time.

## 5. Ingest into the searchable corpus

```bash
plaudio db ingest team-meeting.plaud.json \
  --meeting-id 2026-05-30-team \
  --date 2026-05-30 \
  --title "Team weekly"

plaudio db search "release"
plaudio db search "deadline" --speaker "Alice Smith"
plaudio db list
```
