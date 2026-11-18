"""Differential test of the Oracle against upstream's own test functions.

Not part of the Oracle. For each generated file content, it writes
/app/<name>_est.csv, runs upstream's test function on it, and compares pass or
fail with the Oracle's judge on the same bytes, parsed by the framework's text
parser. It also compares the Oracle's `_csv_rows` with `csv.reader` row for
row on every input that is valid UTF-8. After the random inputs it runs
2,000 files with one field 1 character below to 2 characters above
csv.field_size_limit()'s default (131,072), where csv.reader raises. It prints
the number of differences and writes the Oracle's verdicts, so that runs on
two Python versions can be compared with `cmp`.

Run it in a throwaway container, from the repository root:

    docker run --rm --network none --memory 1g \
      -v "$PWD":/repo:ro \
      -v "$PWD"/conversions/upstream/terminal-bench/rstan-to-pystan/tests:/tests:ro \
      -v /some/empty/dir:/out python:3.13-slim \
      sh -c 'mkdir /app && python3 -B -I \
        /repo/conversions/terminal-bench/rstan-to-pystan/task/hidden/differential.py \
        7 200000 /out/3.13.txt'

and again with python:3.12-slim (the host's Python 3.12) writing /out/3.12.txt.
"""

import csv
import importlib.util
import json
import random
import sys

sys.path.insert(0, "/repo")

from securebench.core.errors import Rejected  # noqa: E402
from securebench.core.evidence import ArtifactEvidence, FileEvidence, FileStatus  # noqa: E402
from securebench.core.task import Parser  # noqa: E402
from securebench.evidence.parsers import parse  # noqa: E402


def load(name: str, path: str):  # noqa: ANN201
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oracle = load("oracle", "/repo/conversions/terminal-bench/rstan-to-pystan/task/hidden/oracle.py")
upstream = load("upstream", "/tests/test_outputs.py")

TESTS = {
    "alpha": upstream.test_alpha_estimation_accuracy,
    "sigma": upstream.test_sigma_estimation_accuracy,
    "rho": upstream.test_rho_estimation_accuracy,
    "beta": upstream.test_beta_estimation_accuracy,
}
HIDDEN = "/repo/conversions/terminal-bench/rstan-to-pystan/task/hidden"


class Resources:
    """Reads hidden/ as the framework does for `plan`."""

    def read(self, relative_path: str) -> bytes:
        with open(f"{HIDDEN}/{relative_path}", "rb") as handle:
            return handle.read()

    def read_json(self, relative_path: str):  # noqa: ANN201
        return json.loads(self.read(relative_path))


CONTEXTS = oracle.plan(Resources(), 0).artifact_contexts


def native(name: str, data: bytes) -> bool:
    with open(f"/app/{name}_est.csv", "wb") as out:
        out.write(data)
    try:
        TESTS[name]()
    except Exception:  # noqa: BLE001 - pytest reports any exception as a failed test
        return False
    return True


def ours(name: str, data: bytes) -> bool:
    path = f"/app/{name}_est.csv"
    try:
        value = parse(Parser.TEXT, data)
        found = FileEvidence(path, FileStatus.PRESENT, value, len(data), "0" * 64, None)
    except Rejected as error:
        found = FileEvidence(path, FileStatus.UNPARSABLE, None, len(data), "0" * 64, str(error))
    return oracle.judge(name, CONTEXTS[name], ArtifactEvidence(name, (found,), ())).passed


def rows_differ(data: bytes) -> object:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    with open("/app/rows.csv", "wb") as out:
        out.write(data)
    with open("/app/rows.csv") as handle:
        try:
            theirs: object = list(csv.reader(handle))
        except csv.Error:
            theirs = "error"
    try:
        mine: object = oracle._csv_rows(text.replace("\r\n", "\n").replace("\r", "\n"))
    except oracle._CsvError:
        mine = "error"
    return None if theirs == mine else (theirs, mine)


# Characters and fragments that matter to strip(), split(","), float() and the
# csv reader: separators, quotes, every line ending text mode knows, Unicode
# whitespace and digits, a byte-order mark, NUL, and the reference's values.
TOKENS = [
    "0", "1", "5", "8", "9", ".", ".", "-", "+", "e", "E", ",", ",", '"', '"', " ", "\t",
    "\n", "\n", "\n", "\r", "\r\n", "a", "nan", "inf", "_", "\x00", "٠", "٩",
    " ", " ", " ", "\x0b", "\x0c", "\x1c", "\x85", "﻿", "1.09", "0.135",
    "0.58", "0.9", "1.5", "-0.03", "-0.81", "0.42", '""', "\xff",
]


def random_text(rng: random.Random) -> bytes:
    data = "".join(rng.choice(TOKENS) for _ in range(rng.randint(0, 24))).encode("utf-8")
    if rng.random() < 0.02:
        data += b"\xff"
    if rng.random() < 0.02:
        data = b"\xef\xbb\xbf" + data
    return data


def near(rng: random.Random, low: float, high: float) -> str:
    """A value at or just beside a range bound, in one of several notations."""
    bound = rng.choice((low, high))
    offset = rng.choice((0.0, 1e-12, 1e-9, 1e-6, 1e-4, 1e-3)) * rng.choice((-1, 1))
    form = rng.choice(("{!r}", "{:.3f}", "{:.6f}", "{:.17g}", "{:e}", "{:.2e}", "{}"))
    return form.format(bound + offset)


LAYOUTS = [
    "{v}\n", "{v}", " {v} \n", "{v}\r\n", "{v},extra\n", '"{v}"\n', "\n\n{v}\n\n",
    "{v}\n\n", "{v} \t\n", "+{v}\n", "{v},\n", '"{v}\n"\n', '"{v}""x"\n', '"{v}"x\n',
    "{v}\r", '"{v}",""\n',
]


def structured(rng: random.Random, name: str) -> bytes:
    ranges = CONTEXTS[name]
    count = len(ranges) + (rng.choice((-1, 1)) if rng.random() < 0.1 else 0)
    rows = []
    for index in range(count):
        low, high = ranges[min(index, len(ranges) - 1)]
        rows.append(rng.choice(LAYOUTS).format(v=near(rng, low, high)))
    return rng.choice(("", "", "\n", "\r\n")).join(rows).encode("utf-8")


LONG_INPUTS = 2000
FIELD_LIMIT = 131072


def long_field(rng: random.Random, name: str) -> bytes:
    """In-range rows, one of which holds a field of about FIELD_LIMIT characters."""
    length = FIELD_LIMIT + rng.choice((-1, 0, 1, 2))
    ranges = CONTEXTS[name]
    rows = [repr((low + high) / 2) for low, high in ranges]
    index = rng.randrange(len(rows))
    value = rows[index]
    kind = rng.choice(("zeros", "spaces", "second", "quoted", "quoted-newlines"))
    if kind == "zeros":
        # Every midpoint's repr has a decimal point, so trailing zeros keep its value.
        row = value + "0" * (length - len(value))
    elif kind == "spaces":
        row = " " * (length - len(value)) + value
    elif kind == "second":
        row = value + "," + "x" * length
    elif kind == "quoted":
        row = '"' + value + "0" * (length - len(value)) + '"'
    else:
        row = '"' + value + "\n" * (length - len(value)) + '"'
    rows[index] = row
    return ("\n".join(rows) + "\n").encode("utf-8")


def main() -> None:
    rng = random.Random(int(sys.argv[1]))
    count = int(sys.argv[2])
    passes = dict.fromkeys(TESTS, 0)
    differences = 0
    verdicts = []
    for iteration in range(count):
        name = rng.choice(list(TESTS))
        data = random_text(rng) if iteration % 2 else structured(rng, name)
        expected = native(name, data)
        passes[name] += expected
        verdict = ours(name, data)
        verdicts.append("1" if verdict else "0")
        rows = rows_differ(data)
        if verdict != expected or rows is not None:
            differences += 1
            if differences <= 20:
                print("DIFFERENCE", name, repr(data)[:300], "native", expected, "rows", repr(rows)[:300])
    print(sys.version.split()[0], "inputs", count, "native passes", passes, "differences", differences)
    long_passes = dict.fromkeys(TESTS, 0)
    long_differences = 0
    for _ in range(LONG_INPUTS):
        name = rng.choice(list(TESTS))
        data = long_field(rng, name)
        expected = native(name, data)
        long_passes[name] += expected
        verdict = ours(name, data)
        verdicts.append("1" if verdict else "0")
        rows = rows_differ(data)
        if verdict != expected or rows is not None:
            long_differences += 1
            if long_differences <= 20:
                print("DIFFERENCE", name, repr(data)[:300], "native", expected, "rows", repr(rows)[:300])
    print("long-field inputs", LONG_INPUTS, "native passes", long_passes, "differences", long_differences)
    with open(sys.argv[3], "w") as out:
        out.write("".join(verdicts))


main()
