"""make-doom-for-mips adapter: run `node /app/vm.js` once and report what it produced.

Assertion-free. It reports the bytes vm.js wrote to stdout and stderr, whether
/tmp/frame.bmp appeared, and what Pillow found in the frame, and compares
nothing. The process handling follows upstream's test_vm_execution: start vm.js
with stderr merged into stdout, wait up to 30 s for /tmp/frame.bmp to exist,
wait 1 s more, terminate, and kill after 5 s. The frame is read after vm.js has
ended, as upstream's later tests do, by frame.py under the baseline's Python and
Pillow.
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import NoReturn

FRAME = Path("/tmp/frame.bmp")
WAIT_FOR_FRAME_SECONDS = 30
STDOUT_BYTES = 512 * 1024
BASELINE_PYTHON = "/usr/local/bin/python3"
FRAME_READER = "/.securebench/evaluation/frame.py"
FRAME_READER_SECONDS = 60


def unable(code: str, message: str) -> NoReturn:
    print(json.dumps({"unable": {"code": code, "message": message}}))
    sys.exit(0)


def run_vm() -> tuple[bytes, bool]:
    with tempfile.NamedTemporaryFile(mode="w+b") as output:
        process = subprocess.Popen(
            ["/usr/bin/node", "/app/vm.js"],
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            cwd="/app",
        )
        started = time.monotonic()
        appeared = True
        while not FRAME.exists():
            if time.monotonic() - started > WAIT_FOR_FRAME_SECONDS:
                appeared = False
                break
            time.sleep(0.1)
        if appeared:
            time.sleep(1)
            process.terminate()
        else:
            process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        output.seek(0)
        return output.read(STDOUT_BYTES), appeared


def read_frame() -> dict[str, object]:
    """frame.py's report: a problem, or the image's size and RGB rows."""
    try:
        result = subprocess.run(
            [BASELINE_PYTHON, "-I", FRAME_READER, str(FRAME)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            cwd="/",
            timeout=FRAME_READER_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        unable("frame_reader", f"frame.py did not run: {type(error).__name__}")
    if result.returncode != 0:
        unable("frame_reader", result.stderr[-2000:].decode("utf-8", "replace"))
    try:
        report = json.loads(result.stdout)
    except ValueError:
        unable("frame_reader", "frame.py printed no JSON")
    if not isinstance(report, dict):
        unable("frame_reader", "frame.py printed no JSON object")
    return report


def main() -> None:
    json.loads(sys.stdin.buffer.read())
    stdout, appeared = run_vm()
    report = read_frame()
    observation: dict[str, object] = {"stdout_hex": stdout.hex(), "frame_appeared": appeared}
    if "problem" in report:
        observation["frame_problem"] = report["problem"]
    else:
        observation["frame"] = {key: report.get(key) for key in ("width", "height", "rows")}
    print(json.dumps({"observation": observation}))


main()
