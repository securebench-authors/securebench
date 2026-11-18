"""Differential test of the recover check against upstream's test.

Not used by the Oracle. It documents how CONVERSION.md's table was made:

    python3 -I differential.py corpus <dir>
        writes the corpus: one file per case, and `special.json` naming the
        cases that are not a regular file.
    docker run --rm --network none --memory 512m \
        -v <upstream>/tests:/tests:ro -v <dir>:/corpus:ro -v <hidden>:/d:ro \
        <baseline> python3 -I /d/differential.py native /corpus
        runs upstream's test function verbatim on each case placed at
        /app/recover.json, on the baseline's Python 3.13 with no locale set
        (UTF-8 mode, as in the verifier's container).
    uv run python -B hidden/differential.py ours <dir>
        runs the framework's `json` parser binding with this pack's file spec,
        then `plan` and `judge` of hidden/oracle.py loaded as the Oracle
        worker loads it.

Each side prints one line per case: its name, then `pass` or `fail`.
"""

import json
import os
import sys
from pathlib import Path

MIB = 1024 * 1024
PAIRS = [
    ("testword02", "10.0"),
    ("testword03", "25.0"),
    ("testword04", "42.0"),
    ("testword05", "50.0"),
    ("testword06", "75.0"),
    ("testword07", "99.0"),
    ("testword08", "99.99"),
    ("testword09", "0.5"),
]


def rows(pairs: list[tuple[str, str]], extra: list[str] = []) -> bytes:
    items = [f'{{"word": "{w}", "value": {v}}}' for w, v in pairs] + extra
    return ("[" + ", ".join(items) + "]").encode()


def corpus() -> dict[str, bytes]:
    ints = [(w, v.removesuffix(".0")) for w, v in PAIRS]
    seven = PAIRS[:6] + PAIRS[7:]
    six = PAIRS[:6]
    exact = rows(PAIRS)
    spray = [f'{{"word": "{w}", "value": {n}}}' for w, _ in PAIRS for n in range(256)]
    spray += [f'{{"word": "{w}", "value": {n / 2}}}' for w, _ in PAIRS for n in range(1, 256, 2)]
    return {
        "reference-8": exact,
        "integers-written-as-ints": rows(ints),
        "all-10-rows": rows([("testword00", "1"), ("testword01", "2")] + PAIRS),
        "seven-of-eight": rows(seven),
        "six-of-eight": rows(six),
        "seven-and-wrong-eighth": rows(seven + [("testword08", "99.98")]),
        "seven-and-unrelated-rows": rows(seven, ['{"word": "x", "value": 1}', '{"word": null, "value": 3}']),
        "exponent-forms": rows([(w, f"{float(v):e}") for w, v in PAIRS]),
        "same-double-longer-literal": rows(six + [("testword08", "99.990000000000000001"), PAIRS[7]]),
        "next-double-up": rows(six + [("testword08", "99.99000000000001"), ("testword09", "0.5000000000000001")]),
        "one-row-repeated": rows(six[:5] + [six[5]] * 3),
        "extra-keys-claiming-pass": rows(PAIRS, ['{"word": "test_json_data", "value": "PASSED", "verdict": "pass"}']),
        "word-unicode-escapes": exact.replace(b"testword02", b"testword\\u0030\\u0032"),
        "word-trailing-space": rows([(w + " ", v) for w, v in PAIRS]),
        "string-values": rows([(w, f'"{v}"') for w, v in PAIRS]),
        "boolean-values": rows([(w, "true") for w, _ in PAIRS]),
        "object-map": ("{" + ", ".join(f'"{w}": {v}' for w, v in PAIRS) + "}").encode(),
        "wrapped-in-object": b'{"rows": ' + exact + b"}",
        "empty-array": b"[]",
        "null": b"null",
        "item-missing-value": rows(PAIRS, ['{"word": "testword00"}']),
        "item-is-array": rows(PAIRS, ['["testword00", 1]']),
        "item-value-is-array": rows(PAIRS, ['{"word": "testword00", "value": [1]}']),
        "item-word-is-object": rows(PAIRS, ['{"word": {"w": 1}, "value": 1}']),
        "one-word-two-values": rows(PAIRS + [("testword02", "11")]),
        "two-words-two-values": rows(PAIRS + [("testword02", "11"), ("testword03", "26")]),
        "word-as-int-and-float": rows(PAIRS + [("testword02", "10")]),
        "word-with-null-too": rows(PAIRS + [("testword02", "null")]),
        "spray": rows([], spray),
        "duplicate-key": exact.replace(b'{"word": ', b'{"word": "x", "word": '),
        "extra-row-nan": rows(PAIRS, ['{"word": "testword00", "value": NaN}']),
        "extra-row-long-integer": rows(PAIRS, ['{"word": "testword00", "value": ' + "1" * 21 + "}"]),
        "extra-row-lone-surrogate": rows(PAIRS, ['{"word": "\\ud800", "value": 1}']),
        "extra-key-deep-nesting": rows(PAIRS, ['{"word": "a", "value": 1, "x": ' + "[" * 70 + "]" * 70 + "}"]),
        "crlf-pretty-printed": json.dumps(json.loads(exact), indent=2).replace("\n", "\r\n").encode(),
        "byte-order-mark": b"\xef\xbb\xbf" + exact,
        "invalid-utf8-in-extra-word": rows(PAIRS, ['{"word": "\xff", "value": 1}']).replace("\xff".encode(), b"\xff"),
        "trailing-garbage": exact + b" x",
        "padded-to-1-mib": exact + b" " * (MIB - len(exact)),
        "padded-past-1-mib": exact + b" " * (MIB - len(exact) + 1),
    }


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
    out = Path("/app/recover.json")
    for name in names(directory):
        if out.is_symlink() or out.is_file():
            out.unlink()
        elif out.is_dir():
            out.rmdir()
        Path("/app/real.json").unlink(missing_ok=True)
        kind = special.get(name)
        if kind == "symlink":
            Path("/app/real.json").write_bytes((directory / "reference-8").read_bytes())
            os.symlink("real.json", out)
        elif kind == "directory":
            out.mkdir()
        elif kind is None:
            out.write_bytes((directory / name).read_bytes())
        try:
            test_outputs.test_json_data()
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
    context = oracle.plan(Resources(), 0).artifact_contexts["recover"]
    spec = FileSpec("/app/recover.json", Parser.JSON, MIB)
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
        evidence = ArtifactEvidence("recover", (file_evidence(spec, read),), ())
        judgment = oracle.judge("recover", context, evidence)
        print(name, "pass" if judgment.passed else "fail")


if __name__ == "__main__":
    command, target = sys.argv[1], Path(sys.argv[2])
    {"corpus": write_corpus, "native": native, "ours": ours}[command](target)
