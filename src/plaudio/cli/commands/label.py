"""`plaudio label AUDIO TRANSCRIPT [--enrol] [--batch-label "L=Name,..."]`"""
from __future__ import annotations
import argparse, json, os, pathlib, platform, subprocess, sys
from collections import defaultdict
from plaudio.core.voicebank import VoiceBank

DEFAULT_TOKEN_FILE = pathlib.Path("~/.huggingface/token").expanduser()

def _bank_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("PLAUDIO_VOICEBANK", str(VoiceBank.default_path()))).expanduser()

def fmt_ms(ms): s = int(ms / 1000); return f"{s//60:02d}:{s%60:02d}"

def find_best_clip(segs, target_speaker, min_dur_s=15, max_dur_s=45):
    spans = []
    cur_start = cur_end = None
    for s in sorted(segs, key=lambda x: x['start_time']):
        if s['speaker'] != target_speaker: continue
        if cur_start is None:
            cur_start, cur_end = s['start_time'], s['end_time']
        elif s['start_time'] - cur_end < 3000:
            cur_end = s['end_time']
        else:
            spans.append((cur_start, cur_end))
            cur_start, cur_end = s['start_time'], s['end_time']
    if cur_start is not None: spans.append((cur_start, cur_end))
    if not spans: return None
    longest = max(spans, key=lambda t: t[1]-t[0])
    if (longest[1]-longest[0])/1000 < min_dur_s: return None
    return (longest[0], min(longest[1], longest[0] + max_dur_s*1000))

def find_enrol_window(segs, target_speaker, max_dur_s=180):
    spans = []
    cur_start = cur_end = None
    for s in sorted(segs, key=lambda x: x['start_time']):
        if s['speaker'] != target_speaker: continue
        if cur_start is None:
            cur_start, cur_end = s['start_time'], s['end_time']
        elif s['start_time'] - cur_end < 5000:
            cur_end = s['end_time']
        else:
            spans.append((cur_start, cur_end))
            cur_start, cur_end = s['start_time'], s['end_time']
    if cur_start is not None: spans.append((cur_start, cur_end))
    if not spans: return None
    longest = max(spans, key=lambda t: t[1]-t[0])
    return (longest[0], min(longest[1], longest[0] + max_dur_s*1000))

def play_clip_bg(audio_path, start_ms, end_ms):
    tmp = pathlib.Path(f"/tmp/plaudio-clip-{start_ms}-{end_ms}.wav")
    dur_s = (end_ms - start_ms) / 1000
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-ss", str(start_ms/1000), "-t", str(dur_s),
             "-i", str(audio_path), "-ar", "16000", "-ac", "1", str(tmp)],
            capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None, f"ffmpeg exit {r.returncode}: {r.stderr[-300:]}"
        if not tmp.exists() or tmp.stat().st_size == 0:
            return None, "ffmpeg produced empty file"
        player = "afplay" if platform.system() == "Darwin" else "ffplay"
        args_list = [player, str(tmp)] if player == "afplay" \
                    else [player, "-nodisp", "-autoexit", "-loglevel", "quiet", str(tmp)]
        proc = subprocess.Popen(args_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc, tmp
    except FileNotFoundError as e:
        return None, f"missing executable: {e}"
    except Exception as e:
        return None, f"unexpected: {e}"

def stop_playback(proc, tmp):
    if proc is not None and proc.poll() is None:
        try:
            proc.terminate(); proc.wait(timeout=2)
        except Exception:
            try: proc.kill()
            except Exception: pass
    if tmp is not None:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass

def save_labels(data, jpath, mapping):
    for s in data['segments']:
        if s['speaker'] in mapping:
            if 'original_speaker' not in s:
                s['original_speaker'] = s['speaker']
            s['speaker'] = mapping[s['speaker']]
    jpath.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def _enrol(name, audio, start_ms, end_ms, hf_token, num_speakers=None):
    print(f"  enrolling {name} from [{fmt_ms(start_ms)}-{fmt_ms(end_ms)}]...")
    bank = VoiceBank.load(_bank_path())
    try:
        bank.enrol_from_audio(
            pathlib.Path(audio),
            name=name,
            start_s=start_ms/1000,
            end_s=end_ms/1000,
            hf_token=hf_token,
            notes=f"via plaudio label interactive labelling",
            num_speakers=num_speakers,
        )
        bank.save(_bank_path())
        print(f"  enrolled {name}")
    except Exception as e:
        print(f"  enrolment failed: {e}", file=sys.stderr)

def cmd_label(args: argparse.Namespace) -> int:
    audio = pathlib.Path(args.audio).expanduser()
    jpath = pathlib.Path(args.transcript).expanduser()
    if not audio.exists(): print(f"audio not found: {audio}", file=sys.stderr); return 2
    if not jpath.exists(): print(f"transcript not found: {jpath}", file=sys.stderr); return 2

    hf_token = ""
    if args.enrol or args.batch_label:
        tf = pathlib.Path(args.hf_token_file).expanduser()
        if not tf.exists():
            print(f"HF token not found at {tf}; enrolment needs it", file=sys.stderr); return 2
        hf_token = tf.read_text().strip()

    data = json.loads(jpath.read_text())
    segs = data.get('segments', [])
    if not segs: print("no segments in json", file=sys.stderr); return 2

    by_spk = defaultdict(list)
    for s in segs:
        by_spk[s['speaker']].append(s)
    durs = {k: sum((x['end_time']-x['start_time'])/1000 for x in v) for k,v in by_spk.items()}
    main_spk = sorted([k for k,v in durs.items() if v > 5], key=lambda k: -durs[k])

    if args.batch_label:
        mapping = {}
        enrol_windows = {}
        for pair in args.batch_label.split(","):
            if "=" not in pair: continue
            spk, name = pair.split("=", 1)
            spk, name = spk.strip(), name.strip()
            if spk not in by_spk:
                print(f"  warn: {spk} not in transcript, skipping"); continue
            mapping[spk] = name
            es = find_enrol_window(by_spk[spk], spk, max_dur_s=180)
            if es: enrol_windows[name] = es
        if mapping:
            save_labels(data, jpath, mapping)
            print(f"batch-labelled {len(mapping)} speakers: {mapping}")
            if args.enrol:
                print("\n=== Enrolling voice profiles ===")
                for name, (s_ms, e_ms) in enrol_windows.items():
                    if name == "Unknown": continue
                    _enrol(name, audio, s_ms, e_ms, hf_token)
        return 0

    print(f"\n{len(main_spk)} clusters to label (> 5s)\n")
    mapping = {}
    enrol_windows = {}

    try:
        for spk in main_spk:
            if not (spk.startswith("SPEAKER_") or spk == "Unknown"):
                print(f"\n{spk}: already labelled, skipping")
                continue
            clip = find_best_clip(by_spk[spk], spk, args.min_dur, args.max_dur)
            if not clip:
                print(f"  {spk}: no clean >={args.min_dur}s clip, skipping")
                continue
            start_ms, end_ms = clip
            dur_s = (end_ms - start_ms) / 1000
            print(f"\n{'='*70}")
            print(f"Speaker: {spk}  |  Airtime: {durs[spk]:.0f}s ({durs[spk]/60:.1f}min)")
            print(f"Clip: {fmt_ms(start_ms)}-{fmt_ms(end_ms)} ({dur_s:.0f}s)")
            in_window = [x for x in by_spk[spk] if x['start_time'] >= start_ms and x['start_time'] < end_ms]
            text = " ".join(x['content'] for x in in_window)
            print(f"Text: \"{text[:500]}\"")
            print()
            playback_proc = playback_tmp = None
            if not args.no_play:
                playback_proc, playback_tmp = play_clip_bg(audio, start_ms, end_ms)
                if playback_proc is None:
                    print(f"  playback error: {playback_tmp}")
                    playback_tmp = None
                else:
                    print("  (playing in background; type at any time to stop)")
            try:
                ans = input("name / [s]kip / [u]nknown / [r]eplay / [q]uit: ").strip()
            except EOFError:
                ans = 'q'
            finally:
                stop_playback(playback_proc, playback_tmp)
            while ans.lower() == 'r':
                if args.no_play:
                    print("  (--no-play; cannot replay)")
                    try: ans = input("name / [s]kip / [u]nknown / [q]uit: ").strip()
                    except EOFError: ans = 'q'
                    break
                pp, pt = play_clip_bg(audio, start_ms, end_ms)
                if pp is None:
                    print(f"  replay error: {pt}")
                else:
                    print("  (replaying)")
                try:
                    ans = input("name / [s]kip / [u]nknown / [r]eplay / [q]uit: ").strip()
                except EOFError:
                    ans = 'q'
                finally:
                    stop_playback(pp, pt)
            if ans.lower() in ('q', 'quit'): raise KeyboardInterrupt
            if ans.lower() in ('s', 'skip', ''): continue
            if ans.lower() in ('u', 'unknown'):
                mapping[spk] = "Unknown"
                save_labels(data, jpath, {spk: "Unknown"})
                print(f"  -> {spk} = Unknown (saved)")
                continue
            mapping[spk] = ans
            enrol_span = find_enrol_window(by_spk[spk], spk, max_dur_s=180)
            enrol_windows[ans] = enrol_span if enrol_span else (start_ms, end_ms)
            es_start, es_end = enrol_windows[ans]
            save_labels(data, jpath, {spk: ans})
            print(f"  -> {spk} = {ans} (saved); enrolment will use [{fmt_ms(es_start)}-{fmt_ms(es_end)}]")
    except KeyboardInterrupt:
        print("\n\n(quitting; labels saved so far)")

    print(f"\nwrote {len(mapping)} labels to {jpath}")
    if args.enrol and enrol_windows:
        print(f"\n=== Enrolling voice profiles ({len(enrol_windows)} people) ===")
        for name, (start_ms, end_ms) in enrol_windows.items():
            if name == "Unknown": continue
            _enrol(name, audio, start_ms, end_ms, hf_token)
    return 0

def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("label", help="interactive speaker labelling")
    p.add_argument("audio")
    p.add_argument("transcript")
    p.add_argument("--enrol", action="store_true")
    p.add_argument("--no-play", action="store_true")
    p.add_argument("--batch-label", type=str)
    p.add_argument("--min-dur", type=int, default=15)
    p.add_argument("--max-dur", type=int, default=15)
    p.add_argument("--hf-token-file", default=str(DEFAULT_TOKEN_FILE))
    p.set_defaults(func=cmd_label)
