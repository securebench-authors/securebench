"""Runs the candidate's extract.js as upstream's tests do and reports what it produced.

Mirrors tests/test_outputs.py step by step: test_extract_js_exists looks at
/app/extract.js; test_output_matches_reference writes /app/new.c, produces
/app/new.o, runs `node /app/extract.js /app/new.o` with standard output in
/app/out.json and parses that file with Python's json module. Upstream
compiles new.o at grading time with the baseline's gcc; we compile it ahead of
time (hidden/derive.sh checks the binary is identical) so that nothing the
candidate can place on the search paths of gcc, as or ld changes the program
under test.

The program and the binary decide the expected memory map, so they are not
in evaluation/: the challenge carries them, the program as text and the binary
in base64.

The adapter decides nothing: the Oracle compares the reported values with the
reference output it keeps on the host.
"""

import base64
import json
import math
import os
import subprocess
import sys

EXTRACT_JS = "/app/extract.js"
INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


def kind_of(value):
    """Name a parsed JSON value's type so the Oracle can apply Python's `!=` to it."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer" if INT64_MIN <= value <= INT64_MAX else "big_integer"
    if isinstance(value, float):
        return "number" if math.isfinite(value) else "non_finite"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "null"
    if isinstance(value, list):
        return "array"
    return "object"


def describe_entry(key, value):
    entry = {"kind": kind_of(value)}
    try:
        key.encode("utf-8")
    except UnicodeEncodeError:
        # A key with a lone surrogate cannot be sent as strict JSON; leaving it
        # out is safe because no reference key contains one.
        pass
    else:
        entry["key"] = key
    if entry["kind"] in ("integer", "number", "boolean"):
        entry[entry["kind"]] = value
    return entry


def main():
    challenge = json.loads(sys.stdin.buffer.read())
    program = challenge["program"].encode("utf-8")
    binary = base64.b64decode(challenge["binary_base64"], validate=True)
    observation = {
        "extract_js_exists": os.path.exists(EXTRACT_JS),
        "extract_js_is_file": os.path.isfile(EXTRACT_JS),
    }

    # Upstream writes these with plain open() and gcc -o, both of which follow
    # a symlink and fail on a directory; a failure there fails upstream's test.
    try:
        with open("/app/new.c", "wb") as target:
            target.write(program)
        with open("/app/new.o", "wb") as target:
            target.write(binary)
        os.chmod("/app/new.o", 0o755)
        out_file = open("/app/out.json", "w")
    except OSError as error:
        print(json.dumps({"unable": {"code": "inputs", "message": str(error)[:1000]}}))
        return

    with out_file:
        try:
            result = subprocess.run(
                ["node", EXTRACT_JS, "/app/new.o"],
                stdin=subprocess.DEVNULL,
                stdout=out_file,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            print(json.dumps({"unable": {"code": "node", "message": str(error)[:1000]}}))
            return
    observation["exit_status"] = result.returncode
    # Upstream passes text=True, so standard error that is not UTF-8 raises
    # in subprocess.run and fails the test.
    try:
        result.stderr.decode("utf-8")
    except UnicodeDecodeError:
        observation["stderr_is_utf8"] = False
    else:
        observation["stderr_is_utf8"] = True

    entries = []
    try:
        with open("/app/out.json", encoding="utf-8") as f:
            output = json.load(f)
    except Exception:
        observation["output_kind"] = "unparsable"
    else:
        observation["output_kind"] = kind_of(output)
        if isinstance(output, dict):
            entries = [describe_entry(key, value) for key, value in output.items()]
    observation["entries"] = entries
    print(json.dumps({"observation": observation}))


main()
