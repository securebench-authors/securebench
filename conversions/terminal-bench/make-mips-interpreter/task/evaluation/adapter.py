"""make-mips-interpreter adapter: run `node /app/vm.js` once and report what it produced.

Assertion-free. It reports the bytes vm.js wrote to stdout and stderr and the
pixels of /tmp/frame.bmp, and compares nothing. The process handling follows
upstream's test_vm_execution: start vm.js from /app with stderr merged into
stdout, wait up to 30 s for /tmp/frame.bmp to exist, wait 1 s more, terminate,
and kill after 5 s. One difference: vm.js's standard input is /dev/null, where
upstream's inherits the verifier's; the program never reads it.

The output goes to the Output Artifact OUTPUT_ARTIFACT, not into the
observation, because the observation is bounded at 4 MiB and an interpreter that
traces its system calls prints megabytes before the line upstream looks for. The
artifact holds the first OUTPUT_BYTES bytes, base64-encoded, the most that fits
the 16 MiB artifact bound. The frame is read after vm.js has ended, as upstream's later
tests do, by frame.py on the baseline's own Python and Pillow 11.2.1, the
version upstream's verifier installs. The challenge is empty: upstream has one
case, with no inputs beyond the baseline's files.
"""

import base64
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

FRAME = Path("/tmp/frame.bmp")
OUTPUT_ARTIFACT = Path("/srv/vm-output.json")
DECODER = [
    "/usr/local/bin/python3",
    "-I",
    "/.securebench/evaluation/frame.py",
    str(FRAME),
]
WAIT_FOR_FRAME_SECONDS = 30
DECODE_TIMEOUT_SECONDS = 60
# 12 MiB less 48 bytes: its base64 plus the JSON wrapper stays under 16 MiB.
OUTPUT_BYTES = 12 * 1024 * 1024 - 48
MAX_SIDE = 4096
MAX_PIXELS = 262144
MAX_DECODER_BYTES = 2 * 1024 * 1024
MAX_RGB_B64_BYTES = 4 * MAX_PIXELS
PROBLEMS = ("empty", "too_large", "undecodable")


def unable(code: str, message: str) -> None:
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
        return output.read(OUTPUT_BYTES), appeared


def read_frame() -> dict[str, object] | str | None:
    """The decoded frame, a problem from PROBLEMS, or None when there is no frame."""
    try:
        size = FRAME.stat().st_size
    except FileNotFoundError:
        return None
    if size == 0:
        return "empty"
    try:
        decoded = subprocess.run(
            DECODER,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            cwd="/",
            timeout=DECODE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return "undecodable"
    if decoded.returncode != 0 or len(decoded.stdout) > MAX_DECODER_BYTES:
        return "undecodable"
    try:
        result = json.loads(decoded.stdout)
    except ValueError:
        return "undecodable"
    if not isinstance(result, dict):
        return "undecodable"
    if set(result) == {"problem"} and result["problem"] in PROBLEMS:
        return str(result["problem"])
    width, height, rgb = result.get("width"), result.get("height"), result.get("rgb_b64")
    if set(result) != {"width", "height", "rgb_b64"} or not isinstance(rgb, str):
        return "undecodable"
    if len(rgb) > MAX_RGB_B64_BYTES:
        return "undecodable"
    if not isinstance(width, int) or not isinstance(height, int):
        return "undecodable"
    if not 1 <= width <= MAX_SIDE or not 1 <= height <= MAX_SIDE or width * height > MAX_PIXELS:
        return "too_large"
    return {"width": width, "height": height, "rgb_b64": rgb}


def main() -> None:
    if json.loads(sys.stdin.buffer.read()) != {}:
        unable("bad_challenge", "the challenge is not empty")
    output, appeared = run_vm()
    frame = read_frame()
    OUTPUT_ARTIFACT.write_text(
        json.dumps({"output_b64": base64.b64encode(output).decode("ascii")})
    )
    observation: dict[str, object] = {"frame_appeared": appeared}
    if frame is None:
        observation["frame_problem"] = "absent"
    elif isinstance(frame, str):
        observation["frame_problem"] = frame
    else:
        observation["frame"] = frame
    print(json.dumps({"observation": observation}))


main()
