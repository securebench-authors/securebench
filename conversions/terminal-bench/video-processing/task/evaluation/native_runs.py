"""Recreates the state the native test session builds up before a test runs.

Natively all of upstream's tests run in file order in one container: the hidden
video sits at /tests/test_video.mp4 from the start, and
test_jump_analyzer_test_video and test_jump_analyzer_imports run after the
script has already run on the videos of the tests before them, keeping every
file those runs left (output.toml, caches, rewritten sources). Each case here
starts from the captured candidate, so the adapter first replays those earlier
runs, unjudged, exactly as upstream's helper runs the script.
"""

import os
import pathlib
import shutil
import subprocess
import tempfile

PYLIB = "/.securebench/evaluation/pylib"
PYTHON = "/usr/local/bin/python3"
SCRIPT = "/app/jump_analyzer.py"


def place_files(challenge: dict) -> None:
    # The pack's copy of the hidden video is on a read-only mount; it goes to
    # the writable path upstream uses, so a script sees what it sees natively.
    for item in challenge["place"]:
        os.makedirs(os.path.dirname(item["to"]), exist_ok=True)
        shutil.copyfile(item["from"], item["to"])


def run_script(video: str, out, err) -> int:
    # The native verifier runs the script with toml==0.10.2 importable; the
    # baseline has no toml, so the same release ships in evaluation/pylib.
    env = dict(os.environ)
    env["PYTHONPATH"] = PYLIB
    completed = subprocess.run(
        [PYTHON, SCRIPT, video],
        stdin=subprocess.DEVNULL,
        stdout=out,
        stderr=err,
        cwd="/app",
        env=env,
    )
    return completed.returncode


def replay_earlier_runs(challenge: dict) -> None:
    # Upstream's helper asserts the video exists before it runs the script, so
    # an earlier test whose video is missing never ran it. Results are ignored:
    # those runs belong to other cases.
    for video in challenge["earlier_runs"]:
        if pathlib.Path(video).exists():
            with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
                run_script(video, out, err)
