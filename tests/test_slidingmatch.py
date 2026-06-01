import pytest
import math
from plaudio.core.slidingmatch import (
    cosine, coalesce_runs, assign_speaker_to_segment, average_by_name,
)


def test_cosine_basic():
    assert cosine([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)
    assert cosine([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)
    assert cosine([1, 0, 0], [-1, 0, 0]) == pytest.approx(-1.0)


def test_coalesce_runs_merges_consecutive_same_label():
    wins = [(0.0, 1.0, "A"), (1.0, 2.0, "A"), (2.0, 3.0, "B"), (3.0, 4.0, "A")]
    runs = coalesce_runs(wins)
    assert runs == [(0.0, 2.0, "A"), (2.0, 3.0, "B"), (3.0, 4.0, "A")]


def test_assign_speaker_picks_max_overlap():
    runs = [(0.0, 5.0, "A"), (5.0, 10.0, "B")]
    seg = {"start_time": 4000, "end_time": 6000}  # ms
    label = assign_speaker_to_segment(seg, runs)
    assert label in ("A", "B")


def test_assign_speaker_returns_unknown_when_no_overlap():
    runs = [(10.0, 20.0, "A")]
    seg = {"start_time": 0, "end_time": 1000}
    assert assign_speaker_to_segment(seg, runs) == "Unknown"


def test_average_by_name_means():
    by_name = {"Alice": [[1.0, 0.0], [0.0, 1.0]]}
    means = average_by_name(by_name)
    assert means["Alice"] == pytest.approx([0.5, 0.5])


def test_cosine_zero_on_dim_mismatch():
    """Documents the behaviour that motivated the dim-mismatch early-raise in
    SlidingMatcher.label_segments: cosine() returns 0.0 on differing dims,
    which would otherwise produce a silent 0-match run when a voicebank built
    under pyannote 3.x (256-dim) is matched against pyannote 4.x (512-dim)."""
    assert cosine([1.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(0.0)
    assert cosine([1.0, 0.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)
