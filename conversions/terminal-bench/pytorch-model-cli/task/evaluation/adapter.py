"""pytorch-model-cli adapter: run the candidate's /app/cli_tool as upstream's tests do.

It runs upstream's commands through /bin/sh from /app, in upstream's order:
first `/app/cli_tool /app/weights.json /app/image.png`
(test_cli_tool_executable); then, as test_cli_tool_output does, it writes the
challenge's images to /app/images/<i>.png and runs the same command on the
first `run` of them. For each run it reports how it ended, the first 1,024 bytes of
standard output, the full output length, and whether all of it was valid UTF-8.
Assertion-free: the Oracle decides.
"""

import base64
import codecs
import json
import os
import selectors
import signal
import subprocess
import sys
import time

SAVE_DIR = "/app/images"
# Upstream gives its whole verifier 900 s and sets no limit per run. Here the
# runs of one case share 840 s, within the case's 900 s.
BUDGET_SECONDS = 840
SHOWN = 1024
CHUNK = 65536


def execute(command: str, deadline: float) -> dict[str, object]:
    process = subprocess.Popen(
        ["/bin/sh", "-c", command],
        cwd="/app",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    assert process.stdout is not None
    shown = bytearray()
    total = 0
    # Validity of the whole output, decoded incrementally so the output need
    # not be kept.
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    valid = True
    timed_out = False
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                timed_out = True
                break
            data = os.read(process.stdout.fileno(), CHUNK)
            if not data:
                break
            total += len(data)
            if len(shown) < SHOWN:
                shown += data[: SHOWN - len(shown)]
            if valid:
                valid = _decodes(decoder, data, final=False)
    if not timed_out:
        try:
            process.wait(max(0.0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
    if timed_out:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
    process.stdout.close()
    if valid:
        valid = _decodes(decoder, b"", final=True)
    return {
        "ending": "timed_out" if timed_out else "exited",
        "stdout": bytes(shown).decode("utf-8", "replace"),
        "stdout_bytes": total,
        "utf8": valid,
    }


def _decodes(decoder: codecs.IncrementalDecoder, data: bytes, final: bool) -> bool:
    try:
        decoder.decode(data, final)
    except UnicodeDecodeError:
        return False
    return True


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    deadline = time.monotonic() + BUDGET_SECONDS
    # Upstream runs test_cli_tool_executable before test_cli_tool_output writes
    # its images, so /app/images does not exist yet during that run.
    image_png = execute("/app/cli_tool /app/weights.json /app/image.png", deadline)
    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        for index, image in enumerate(challenge["images"]):
            with open(os.path.join(SAVE_DIR, f"{index}.png"), "wb") as f:
                f.write(base64.b64decode(image, validate=True))
    except OSError as error:
        # Upstream's test fails the same way when it cannot write its images.
        print(json.dumps({"unable": {"code": "images", "message": str(error)[:4096]}}))
        return
    runs = [
        execute(f"/app/cli_tool /app/weights.json {SAVE_DIR}/{index}.png", deadline)
        for index in range(challenge["run"])
    ]
    print(json.dumps({"observation": {"image_png": image_png, "images": runs}}))


main()
