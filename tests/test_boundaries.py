"""Boundary tests: plaudio.core MUST NOT depend on plaudio.plaud."""
import pathlib, re

CORE_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "plaudio" / "core"
# Match only actual import statements (not comments or docstrings).
# A genuine import begins at line-start (possibly indented), never inside a comment.
BAD = re.compile(
    r"^[ \t]*(?:from\s+plaudio\.plaud|import\s+plaudio\.plaud)",
    re.MULTILINE,
)

def test_core_never_imports_plaud():
    offenders = []
    for py in CORE_DIR.rglob("*.py"):
        text = py.read_text()
        if BAD.search(text):
            offenders.append(str(py))
    assert not offenders, f"plaudio.core imports plaudio.plaud in: {offenders}"
