"""Compare the Oracle with upstream's test_primers on crafted primers files.

Upstream's calc_tm_oligotm is replaced by a lookup in hidden/oligotm.json,
which holds real oligotm output for every sequence the test can pass it; a
sequence outside the table raises KeyError and stops the comparison. Run from
the repository root:

    PYTHONDONTWRITEBYTECODE=1 uv run python -B \
      conversions/terminal-bench/dna-insert/task/hidden/differential.py \
      conversions/terminal-bench/dna-insert/task/hidden \
      conversions/upstream/terminal-bench/dna-insert/tests
"""

import importlib.util
import json
import pathlib
import sys
import tempfile

from securebench.core.errors import Rejected
from securebench.core.evidence import ArtifactEvidence, FileEvidence, FileStatus
from securebench.core.task import Parser
from securebench.evidence.parsers import parse

hidden = pathlib.Path(sys.argv[1])
tests = pathlib.Path(sys.argv[2])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oracle = load("oracle", hidden / "oracle.py")
upstream = load("test_outputs", tests / "test_outputs.py")
table = json.loads((hidden / "oligotm.json").read_text())
stdout_of = {row["sequence"]: row["stdout"] for strand in ("forward", "reverse") for row in table[strand].values()}
upstream.calc_tm_oligotm = lambda seq: float(stdout_of[seq].strip())
primers_file = pathlib.Path(tempfile.mkdtemp()) / "primers.fasta"
upstream.Path = lambda _: primers_file


class Resources:
    def read_json(self, path):
        return json.loads((hidden / path).read_text())


context = oracle.plan(Resources(), 0).artifact_contexts["primers"]


def native(data: bytes) -> bool:
    primers_file.write_bytes(data)
    try:
        upstream.test_primers()
    except (AssertionError, UnicodeDecodeError):
        return False
    return True


def securebench(data: bytes) -> bool:
    try:
        found = FileEvidence(primers_file.name, FileStatus.PRESENT, parse(Parser.TEXT, data), len(data), "", None)
    except Rejected as error:
        found = FileEvidence(primers_file.name, FileStatus.UNPARSABLE, None, len(data), None, str(error))
    return oracle.judge("primers", context, ArtifactEvidence("primers", (found,), ())).passed


expected = json.loads((hidden / "expected.json").read_text())
rc = upstream.rc
insert, vector1, vector2 = expected["insert"], expected["vector1"], expected["vector2"]


def pair(fwd_anneal: int, rev_anneal: int) -> tuple[str, str]:
    # The reference's split of the insert: 20 nucleotides on the forward
    # primer, 19 on the reverse one.
    return insert[-20:] + vector2[:fwd_anneal], rc(vector1[-rev_anneal:] + insert[:-20])


# Every pair of annealed lengths 15 to 45 (so every temperature threshold),
# plus 13 and 14, which the length check rejects. Both vectors are 45
# nucleotides long, so no primer can overlap them over more.
cases = []
for f in range(13, 46):
    for r in range(13, 46):
        fwd, rev = pair(f, r)
        cases.append(f">f\n{fwd}\n>r\n{rev}\n")
# Line handling: universal newlines, rstrip, lower-casing, counting, order.
fwd, rev = pair(15, 41)
cases += [
    f">f\n{fwd}\n>r\n{rev}",
    f">f\r\n{fwd}\r\n>r\r\n{rev}\r\n",
    f">f\r{fwd}\r>r\r{rev}\r",
    f">f\n{fwd.upper()}  \t\n>r\n{rev}\x0c\n",
    f">f\n{fwd}\n>r\n{rev}\n\n",
    f">f\n{fwd}\n>r\n{rev}\n  \n",
    f"\n{fwd}\n\n{rev}\n",
    f">r\n{rev}\n>f\n{fwd}\n",
    f">f\n{fwd}x\n>r\n{rev}\n",
    f">f\n\n>r\n{rev}\n",
    f">f\n {fwd}\n>r\n{rev}\n",
    f">f\n{fwd} \n>r\n{rev}\n",
    f">f x\n{fwd}\n>r\n{rev}\n",
    f">f\x0bx\n{fwd}\n>r\n{rev}\n",
    f">f\n{fwd}\x1c\n>r\n{rev}\n",
    f">f\n{fwd}\r\r\n>r\n{rev}\n",
    f"﻿>f\n{fwd}\n>r\n{rev}\n",
    f">f\n{fwd + insert}\n>r\n{rev}\n",
    f">f\n{insert + vector2[:15]}\n>r\n{rc(vector1[-41:])}\n",
    "",
    "\n",
    f">f\n{fwd}\n>r\n{rev}\n" * 2,
]
encoded = [case.encode() for case in cases]
encoded.append(b">f\n" + fwd.encode() + b"\n>r\xff\n" + rev.encode() + b"\n")
mismatches = [(data[:60], native(data), securebench(data)) for data in encoded if native(data) != securebench(data)]
print(f"{len(encoded)} files, {sum(map(native, encoded))} pass natively; mismatches: {mismatches}")
