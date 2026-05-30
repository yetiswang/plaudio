import subprocess, sys
from pathlib import Path
from plaudio import __version__

def test_version_attribute_exists():
    assert __version__ == "0.1.0"

def test_cli_version_subcommand():
    # Resolve the plaudio script next to the current interpreter so the test
    # works whether pytest is invoked via the venv or via an absolute path.
    plaudio_bin = Path(sys.executable).parent / "plaudio"
    cmd = [str(plaudio_bin), "version"] if plaudio_bin.exists() else [sys.executable, "-m", "plaudio.cli.main", "version"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0
    assert __version__ in r.stdout
