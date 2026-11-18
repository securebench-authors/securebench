"""Differential test of the answer check against upstream's tests.

Not used by the Oracle. It documents how CONVERSION.md's table was made:

    python3 -I differential.py corpus <dir>
        writes the corpus: one file per case, and `special.json` naming the
        cases that are not a regular file.
    docker run --rm --network none --memory 512m \
        -v <upstream>/tests:/tests:ro -v <dir>:/corpus:ro -v <hidden>:/d:ro \
        <baseline> python3 -I /d/differential.py native /corpus
        runs upstream's two test functions verbatim on each case placed at
        /app/out.txt, on the baseline's Python 3.13 with no locale set (UTF-8
        mode, as in the verifier's container).
    uv run python hidden/differential.py ours <dir>
        runs the framework's `text` parser binding with this pack's file spec,
        then `plan` and `judge` of hidden/oracle.py loaded as the Oracle
        worker loads it.

Each side prints one line per case: its name, then `pass` or `fail`.
"""

import json
import os
import sys
from pathlib import Path

FLAG = "flag{gc0d3_iz_ch4LLenGiNg}"
MIB = 1024 * 1024


def corpus() -> dict[str, bytes]:
    flag = FLAG.encode()
    cases = {
        "flag-newline": flag + b"\n",
        "flag-bare": flag,
        "flag-tesseract-form-feed": flag + b"\n\x0c",
        "flag-crlf": flag + b"\r\n",
        "flag-lone-cr": b"\r" + flag + b"\r",
        "flag-spaces-tabs-blank-lines": b"\n\n  \t" + flag + b" \t\n\n\n",
        "flag-vertical-tab-and-separators": b"\x0b\x1c\x1d\x1e\x1f" + flag + b"\x1f\x0b",
        "flag-unicode-spaces": " 　 \u0085".encode() + flag + "   ".encode(),
        "flag-padded-to-1-mib": flag + b" " * (MIB - len(flag)),
        "flag-padded-past-1-mib": flag + b" " * (MIB - len(flag) + 1),
        "flag-byte-order-mark": b"\xef\xbb\xbf" + flag,
        "flag-zero-width-space": flag + "​".encode(),
        "flag-nul": b"\x00" + flag + b"\x00",
        "flag-invalid-utf8": flag + b"\n\xff",
        "flag-twice": flag + b"\n" + flag + b"\n",
        "flag-pass-claim": flag + b"\nPASSED test_hello_file_content\n",
        "flag-quoted": b'"' + flag + b'"\n',
        "flag-prefixed": b"The text shows: " + flag + b"\n",
        "flag-inner-space": flag.replace(b"_iz_", b"_iz _") + b"\n",
        "flag-inner-cr": flag.replace(b"_iz_", b"_iz\r_") + b"\n",
        "lowercase": FLAG.lower().encode() + b"\n",
        "uppercase": FLAG.upper().encode() + b"\n",
        "letter-o-for-zero": FLAG.replace("0", "O").encode() + b"\n",
        "fullwidth": "".join(chr(ord(c) + 0xFEE0) for c in FLAG).encode() + b"\n",
        "cyrillic-a": FLAG.replace("a", "а").encode() + b"\n",
        "no-braces": b"gc0d3_iz_ch4LLenGiNg\n",
        "spray": (FLAG.lower() + "\n" + FLAG + "\n").encode(),
        "empty": b"",
        "whitespace-only": b" \n\t\n",
    }
    return cases


SPECIAL = {"absent": "absent", "symlink-to-flag": "symlink", "directory": "directory"}


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
    out = Path("/app/out.txt")
    for name in names(directory):
        if out.is_symlink() or out.is_file():
            out.unlink()
        elif out.is_dir():
            out.rmdir()
        Path("/app/real.txt").unlink(missing_ok=True)
        kind = special.get(name)
        if kind == "symlink":
            Path("/app/real.txt").write_text(FLAG + "\n")
            os.symlink("real.txt", out)
        elif kind == "directory":
            out.mkdir()
        elif kind is None:
            out.write_bytes((directory / name).read_bytes())
        try:
            test_outputs.test_hello_file_exists()
            test_outputs.test_hello_file_content()
            verdict = "pass"
        except Exception:
            verdict = "fail"
        print(name, verdict)


def ours(directory: Path) -> None:
    from securebench.core.evidence import ArtifactEvidence, FileStatus, FoundFile, FileRead
    from securebench.core.task import FileSpec, Parser
    from securebench.evidence.binding import file_evidence
    from securebench.core import jsondata
    from securebench.oracle.worker import load
    import hashlib

    hidden = Path(__file__).resolve().parent

    class Resources:
        def read(self, relative_path: str) -> bytes:
            return (hidden / relative_path).read_bytes()

        def read_json(self, relative_path: str) -> jsondata.JsonValue:
            data = self.read(relative_path)
            return jsondata.decode(data, len(data))

    oracle = load(hidden / "oracle.py")
    context = oracle.plan(Resources(), 0).artifact_contexts["answer"]
    spec = FileSpec("/app/out.txt", Parser.TEXT, MIB)
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
