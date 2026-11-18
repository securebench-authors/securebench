"""Runs /app/jump_analyzer.py on one video and reports what it produced.

This follows upstream's _test_jump_analyzer_video step by step: the video must
exist, the script runs as `python /app/jump_analyzer.py <video>` in /app with its
output captured as text, then /app/output.toml is loaded with toml 0.10.2 and the
two frame numbers are read. Before that it replays the runs of the earlier
upstream tests (native_runs.py). The adapter reports each fact; the Oracle
holds the frame ranges and decides.
"""

import codecs
import io
import json
import math
import os
import pathlib
import stat
import sys
import tempfile

# The baseline image has no toml and the Evaluation has no network, so the
# toml==0.10.2 the native verifier installs ships here unchanged.
sys.path.insert(0, "/.securebench/evaluation/pylib")
sys.path.insert(0, "/.securebench/evaluation")

import toml  # noqa: E402
from native_runs import place_files, replay_earlier_runs, run_script  # noqa: E402

# Everything the adapter needs after the candidate has run is imported above,
# so files the candidate rewrites while it runs cannot change the adapter's code.

OUTPUT = "/app/output.toml"
FIELDS = {"takeoff": "jump_takeoff_frame_number", "landing": "jump_land_frame_number"}
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
INT_BOUND = 2**63 - 1


def _short(text: str, limit: int) -> str:
    return text.encode("utf-8", "replace")[-limit:].decode("utf-8", "ignore")


def _decodes_as_utf8(stream) -> bool:
    # subprocess.run(..., text=True) decodes the captured output strictly with
    # the locale encoding, which is UTF-8 in the verifier (C locale, so Python's
    # UTF-8 mode). Output that does not decode makes the native test fail.
    stream.seek(0)
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    try:
        while chunk := stream.read(1 << 20):
            decoder.decode(chunk)
        decoder.decode(b"", final=True)
    except UnicodeDecodeError:
        return False
    return True


def _tail(stream) -> str:
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(max(0, size - 1024))
    return stream.read().decode("utf-8", "replace")


def _field(data: dict, name: str) -> dict:
    if name not in data:
        return {"kind": "absent"}
    value = data[name]
    # Upstream compares with `low <= value <= high`. Python compares bools,
    # ints and floats numerically, and raises TypeError for anything else.
    if isinstance(value, bool):
        return {"kind": "boolean", "value": int(value)}
    if isinstance(value, int):
        if -INT_BOUND <= value <= INT_BOUND:
            return {"kind": "integer", "value": value}
        return {"kind": "out_of_bounds"}
    if isinstance(value, float):
        if math.isfinite(value):
            return {"kind": "float", "value": value}
        return {"kind": "out_of_bounds"}
    return {"kind": "other", "type": type(value).__name__[:64]}


def _nonblocking(path, flags):
    # A FIFO left at the output path would otherwise block the adapter.
    return os.open(path, flags | os.O_NONBLOCK)


def _read_output(run: dict) -> None:
    if not pathlib.Path(OUTPUT).exists():
        run["output_toml"] = "absent"
        return
    try:
        with io.open(OUTPUT, encoding="utf-8", opener=_nonblocking) as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("output.toml is not a regular file")
            if info.st_size > MAX_OUTPUT_BYTES:
                raise ValueError(f"output.toml is larger than {MAX_OUTPUT_BYTES} bytes")
            # toml.load(path) opens the file with io.open(encoding="utf-8") and
            # calls loads() on its text; this does the same on the open handle.
            data = toml.loads(handle.read())
    except Exception as error:  # upstream turns any load error into a failure
        run["output_toml"] = "unreadable"
        run["detail"] = _short(f"{type(error).__name__}: {error}", 512)
        return
    run["output_toml"] = "parsed"
    for key, name in FIELDS.items():
        run[key] = _field(data, name)


def main() -> None:
    challenge = json.load(sys.stdin)
    place_files(challenge)
    replay_earlier_runs(challenge)
    video = challenge["video"]
    observation: dict = {"video_exists": pathlib.Path(video).exists()}
    if observation["video_exists"]:
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            returncode = run_script(video, out, err)
            run: dict = {
                "returncode": returncode,
                "output_decodes": _decodes_as_utf8(out) and _decodes_as_utf8(err),
                "stderr_tail": _tail(err),
            }
        _read_output(run)
        observation["run"] = run
    sys.stdout.write(json.dumps({"observation": observation}))


if __name__ == "__main__":
    main()
