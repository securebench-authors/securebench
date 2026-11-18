"""Differential test of the answer check against upstream's test.

Not used by the Oracle. It documents how CONVERSION.md's table was made:

    python3 -I differential.py corpus <dir>
        writes the corpus: one file per case, and `special.json` naming the
        cases that are not a regular file.
    docker run --rm --network none --memory 512m \
        -v <upstream>/tests:/tests:ro -v <dir>:/corpus:ro -v <hidden>:/d:ro \
        -v <uv cpython 3.13>:/py:ro \
        <baseline> /py/bin/python3.13 -I /d/differential.py native /corpus
        runs upstream's test function verbatim on each case placed at
        /app/move.txt, on a uv-managed CPython 3.13 (the kind of interpreter
        `uvx -p 3.13` gives upstream's verifier) with no locale set, so in
        UTF-8 mode, as in the verifier's container.
    uv run python -B hidden/differential.py ours <dir>
        runs the framework's `text` parser binding with this pack's file spec,
        then `plan` and `judge` of hidden/oracle.py loaded as the Oracle
        worker loads it.

Each side prints one line per case: its name, then `pass` or `fail`.
"""

import json
import os
import sys
from pathlib import Path

MIB = 1024 * 1024
ANSWER = b"e2e4\ng2g4"


def corpus() -> dict[str, bytes]:
    cases = {
        "reference-form": ANSWER,
        "reversed-trailing-newline": b"g2g4\ne2e4\n",
        "one-line-space": b"e2e4 g2g4\n",
        "one-line-tab": b"e2e4\tg2g4",
        "crlf": b"e2e4\r\ng2g4\r\n",
        "lone-cr": b"\re2e4\rg2g4\r",
        "form-feed-vertical-tab": b"\x0ce2e4\x0bg2g4\x0c",
        "separators-1c-1f": b"\x1ce2e4\x1d\x1eg2g4\x1f",
        "blank-lines-around": b"\n\n  e2e4\n\n\n g2g4  \n\n",
        "unicode-spaces": "\u00a0e2e4\u3000g2g4\u2028\u2029\u0085\u2003".encode(),
        "padded-to-1-mib": ANSWER + b" " * (MIB - len(ANSWER)),
        "padded-past-1-mib": ANSWER + b" " * (MIB - len(ANSWER) + 1),
        "byte-order-mark": b"\xef\xbb\xbf" + ANSWER,
        "zero-width-space-separator": "e2e4\u200bg2g4".encode(),
        "mongolian-vowel-separator": "e2e4\u180eg2g4".encode(),
        "nul-separator": b"e2e4\x00g2g4",
        "no-separator": b"e2e4g2g4\n",
        "invalid-utf8-after": ANSWER + b"\n\xff",
        "duplicate-move": b"e2e4\ne2e4\ng2g4\n",
        "both-twice": b"e2e4\ng2g4\ne2e4\ng2g4\n",
        "only-e2e4": b"e2e4\n",
        "only-g2g4": b"g2g4\n",
        "extra-move": b"e2e4\ng2g4\nh5h6\n",
        "pass-claim": ANSWER + b"\nPASSED test_move_correct\n",
        "comma": b"e2e4,g2g4\n",
        "uppercase": b"E2E4\nG2G4\n",
        "san": b"Qe4#\ng4#\n",
        "promotion-suffix": b"e2e4q\ng2g4\n",
        "fullwidth": "\uff45\uff12\uff45\uff14\ng2g4".encode(),
        "empty": b"",
        "whitespace-only": b" \n\t\n",
    }
    return cases


SPECIAL = {"absent": "absent", "symlink-to-answer": "symlink", "directory": "directory"}


def write_corpus(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    for name, data in corpus().items():
        (directory / name).write_bytes(data)
    (directory / "special.json").write_text(json.dumps(SPECIAL))


def names(directory: Path) -> list[str]:
    special = json.loads((directory / "special.json").read_text())
    return sorted([p.name for p in directory.iterdir() if p.name != "special.json"] + list(special))


def native(directory: Path) -> None:
    sys.path.insert(0, "/tests")
    import test_outputs  # upstream's tests/test_outputs.py, verbatim

    special = json.loads((directory / "special.json").read_text())
    out = Path("/app/move.txt")
    for name in names(directory):
        if out.is_symlink() or out.is_file():
            out.unlink()
        elif out.is_dir():
            out.rmdir()
        Path("/app/real.txt").unlink(missing_ok=True)
        kind = special.get(name)
        if kind == "symlink":
            Path("/app/real.txt").write_bytes(ANSWER)
            os.symlink("real.txt", out)
        elif kind == "directory":
            out.mkdir()
        elif kind is None:
            out.write_bytes((directory / name).read_bytes())
        try:
            test_outputs.test_move_correct()
            verdict = "pass"
        except Exception:
            verdict = "fail"
        print(name, verdict)


def ours(directory: Path) -> None:
    import hashlib

    from securebench.core import jsondata
    from securebench.core.evidence import ArtifactEvidence, FileRead, FileStatus, FoundFile
    from securebench.core.task import FileSpec, Parser
    from securebench.evidence.binding import file_evidence
    from securebench.oracle.worker import load

    hidden = Path(__file__).resolve().parent

    class Resources:
        def read(self, relative_path: str) -> bytes:
            return (hidden / relative_path).read_bytes()

        def read_json(self, relative_path: str) -> jsondata.JsonValue:
            data = self.read(relative_path)
            return jsondata.decode(data, len(data))

    oracle = load(hidden / "oracle.py")
    context = oracle.plan(Resources(), 0).artifact_contexts["moves"]
    spec = FileSpec("/app/move.txt", Parser.TEXT, MIB)
    special = json.loads((directory / "special.json").read_text())
    for name in names(directory):
        kind = special.get(name)
        read: FileRead
        if kind == "absent":
            read = FileStatus.ABSENT
        elif kind is not None:
            read = FileStatus.NOT_REGULAR
        else:
            data = (directory / name).read_bytes()
            read = FoundFile(data, hashlib.sha256(data).hexdigest(), False)
        evidence = ArtifactEvidence("moves", (file_evidence(spec, read),), ())
        judgment = oracle.judge("moves", context, evidence)
        print(name, "pass" if judgment.passed else "fail")


if __name__ == "__main__":
    command, target = sys.argv[1], Path(sys.argv[2])
    {"corpus": write_corpus, "native": native, "ours": ours}[command](target)
