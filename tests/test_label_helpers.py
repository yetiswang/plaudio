from plaudio.cli.commands.label import find_best_clip, find_enrol_window

SEGS = [
    {"speaker": "A", "start_time": 0,     "end_time": 1000,  "content": "x"},
    {"speaker": "A", "start_time": 1000,  "end_time": 16000, "content": "y"},
    {"speaker": "B", "start_time": 16000, "end_time": 18000, "content": "z"},
    {"speaker": "A", "start_time": 18000, "end_time": 20000, "content": "w"},
]

def test_find_best_clip_returns_longest_span_for_target():
    clip = find_best_clip(SEGS, "A", min_dur_s=10, max_dur_s=60)
    assert clip is not None
    assert clip[0] == 0 and clip[1] >= 16000

def test_find_best_clip_none_if_target_too_short():
    short = [{"speaker": "A", "start_time": 0, "end_time": 1000, "content": "x"}]
    assert find_best_clip(short, "A", min_dur_s=10, max_dur_s=60) is None

def test_find_enrol_window_allows_5s_gap():
    segs = [
        {"speaker": "A", "start_time": 0,    "end_time": 5000,  "content": "a"},
        {"speaker": "B", "start_time": 5500, "end_time": 6000,  "content": "b"},
        {"speaker": "A", "start_time": 8000, "end_time": 15000, "content": "c"},
    ]
    clip = find_enrol_window(segs, "A", max_dur_s=60)
    assert clip is not None and clip[0] == 0
