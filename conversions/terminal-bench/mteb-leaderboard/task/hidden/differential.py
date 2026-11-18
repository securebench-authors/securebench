"""Differential test of the answer check against upstream's tests.

Not used by the Oracle. It documents how CONVERSION.md's table was made:

    python3 -I differential.py corpus <dir>
        writes the corpus: one file per case, and `special.json` naming the
        cases that are not a regular file.
    docker run --rm --network none --memory 512m -e LANG=C.UTF-8 \
        -v <upstream>/tests:/tests:ro -v <dir>:/corpus:ro -v <hidden>:/d:ro \
        python:3.13-slim-bookworm python3 -I /d/differential.py native /corpus
        runs upstream's two test functions verbatim on each case placed at
        /app/result.txt, on Python 3.13 with LANG=C.UTF-8, as in the
        verifier, which runs pytest on uv's Python 3.13 in the baseline (whose
        image sets LANG=C.UTF-8).
    PYTHONDONTWRITEBYTECODE=1 uv run python hidden/differential.py ours <dir>
        runs the framework's `text` parser binding with this pack's file spec,
        then `plan` and `judge` of hidden/oracle.py loaded as the Oracle
        worker loads it.

Each side prints one line per case: its name, then `pass` or `fail`.
"""

import json
import os
import sys
from pathlib import Path

MODEL = "GritLM/GritLM-7B"
MIB = 1024 * 1024


def corpus() -> dict[str, bytes]:
    name = MODEL.encode()
    return {
        "model-bare": name,
        "model-newline": name + b"\n",
        "model-crlf": name + b"\r\n",
        "model-lone-cr": name + b"\r",
        "model-spaces-tabs": b"  \t" + name + b" \t\n",
        "model-vertical-tab-form-feed-separators": b"\x0b\x0c\x1c\x1d\x1e\x1f" + name + b"\x1f\x0b",
        "model-unicode-spaces-line-separators": " 　 \u0085 ".encode() + name + "  ".encode(),
        "model-padded-to-1-mib": name + b" " * (MIB - len(name)),
        "model-padded-past-1-mib": name + b" " * (MIB - len(name) + 1),
        "model-leading-blank-line": b"\n" + name + b"\n",
        "model-trailing-blank-line": name + b"\n\n",
        "model-trailing-whitespace-line": name + b"\n \n",
        "model-cr-then-line": name + b"\r\n\r\n",
        "model-cr-inside": b"GritLM/\rGritLM-7B",
        "model-byte-order-mark": b"\xef\xbb\xbf" + name,
        "model-zero-width-space": name + "​".encode(),
        "model-nul": name + b"\x00",
        "model-invalid-utf8": name + b"\xff",
        "model-twice": name + b"\n" + name + b"\n",
        "model-and-score": name + b"\n0.6312\n",
        "model-pass-claim": name + b"\nPASSED test_data_matches\n",
        "model-quoted": b'"' + name + b'"\n',
        "model-prefixed": b"Best model: " + name + b"\n",
        "lowercase": MODEL.lower().encode(),
        "no-organization": b"GritLM-7B",
        "folder-name": b"GritLM__GritLM-7B",
        "hub-url": b"https://huggingface.co/GritLM/GritLM-7B",
        "other-model": b"GritLM/GritLM-8x7B",
        "empty": b"",
        "newline-only": b"\n",
        "whitespace-only": b" \t",
    }


SPECIAL = {"absent": "absent", "symlink-to-model": "symlink", "directory": "directory"}


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
    Path("/app").mkdir(exist_ok=True)
    out = Path("/app/result.txt")
    for name in names(directory):
        if out.is_symlink() or out.is_file():
            out.unlink()
        elif out.is_dir():
            out.rmdir()
        Path("/app/real.txt").unlink(missing_ok=True)
        kind = special.get(name)
        if kind == "symlink":
            Path("/app/real.txt").write_text(MODEL)
            os.symlink("real.txt", out)
        elif kind == "directory":
            out.mkdir()
        elif kind is None:
            out.write_bytes((directory / name).read_bytes())
        try:
            test_outputs.test_result_exists()
            test_outputs.test_data_matches()
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
    context = oracle.plan(Resources(), 0).artifact_contexts["answer"]
    spec = FileSpec("/app/result.txt", Parser.TEXT, MIB)
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
        evidence = ArtifactEvidence("answer", (file_evidence(spec, read),), ())
        judgment = oracle.judge("answer", context, evidence)
        print(name, "pass" if judgment.passed else "fail")


if __name__ == "__main__":
    command, target = sys.argv[1], Path(sys.argv[2])
    {"corpus": write_corpus, "native": native, "ours": ours}[command](target)
