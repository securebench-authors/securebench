"""Differential test of the about and layout checks against upstream's tests.

Not used by the Oracle. It documents how CONVERSION.md's comparison was made:

    python3 -I differential.py corpus <dir>
        writes the corpus: for each check, one file per case, and
        `special.json` naming the cases that are not a regular file.
    docker run --rm --network none --memory 1g \
        -v <upstream>/tests:/tests:ro -v <dir>:/corpus:ro -v <hidden>:/d:ro \
        <baseline> python3 -I /d/differential.py native /corpus
        runs upstream's test functions verbatim on each case placed at the
        checked path, with /app/resources/patch_files as the baseline has it,
        on the baseline's Python 3.13.
    docker run --rm --network none --memory 1g \
        -v <repository>:/r:ro -v <dir>:/corpus:ro -w /r -e PYTHONPATH=/r \
        <stock image> python3 -B -I /r/<pack>/hidden/differential.py ours /corpus
        runs the framework's `text` parser binding with this pack's file
        specs, then `plan` and `judge` of hidden/oracle.py loaded as the
        Oracle worker loads it. (-I ignores PYTHONPATH, so `ours` adds the
        working directory itself.)

Each side prints one line per case: the check, the case name, then `pass`
or `fail`.
"""

import json
import os
import sys
from pathlib import Path

MIB = 1024 * 1024
LIMIT = 16 * MIB
CHECKS = {
    "about": ("/app/personal-site/_includes/about.md", "about.md", "test_about_file"),
    "layout": ("/app/personal-site/_layouts/default.html", "default.html", "test_layout_file"),
}


def variants(expected: bytes) -> dict[str, bytes]:
    middle = expected.find(b" ")
    return {
        "exact": expected,
        "trailing-newline": expected + b"\n",
        "all-six-ascii-whitespace-around": b" \t\n\r\x0b\x0c" + expected + b"\x0c\x0b\r\n\t ",
        "trailing-file-separator-x1c": expected + b"\x1c",
        "trailing-nbsp": expected + " ".encode(),
        "trailing-next-line-x85": expected + "\u0085".encode(),
        "trailing-line-separator-u2028": expected + " ".encode(),
        "trailing-nul": expected + b"\x00",
        "trailing-invalid-utf8": expected + b"\xff",
        "byte-order-mark": b"\xef\xbb\xbf" + expected,
        "crlf-line-endings": expected.replace(b"\n", b"\r\n"),
        "last-byte-dropped": expected.rstrip()[:-1],
        "inner-space-doubled": expected[:middle] + b" " + expected[middle:],
        "empty": b"",
        "padded-to-16-mib": expected + b" " * (LIMIT - len(expected)),
        "padded-past-16-mib": expected + b" " * (LIMIT - len(expected) + 1),
    }


SPECIAL = {"absent": "absent", "symlink-to-reference": "symlink", "directory": "directory"}


def write_corpus(directory: Path) -> None:
    hidden = Path(__file__).resolve().parent
    directory.mkdir(parents=True, exist_ok=False)
    for check, (_, hidden_name, _) in CHECKS.items():
        (directory / check).mkdir()
        for name, data in variants((hidden / hidden_name).read_bytes()).items():
            (directory / check / name).write_bytes(data)
    (directory / "special.json").write_text(json.dumps(SPECIAL))


def names(directory: Path, check: str) -> list[str]:
    special = json.loads((directory / "special.json").read_text())
    return sorted([p.name for p in (directory / check).iterdir()] + list(special))


def native(directory: Path) -> None:
    sys.path.insert(0, "/tests")
    import test_outputs  # upstream's tests/test_outputs.py, verbatim

    special = json.loads((directory / "special.json").read_text())
    for check, (path, hidden_name, test) in CHECKS.items():
        out = Path(path)
        for name in names(directory, check):
            if out.is_symlink() or out.is_file():
                out.unlink()
            elif out.is_dir():
                out.rmdir()
            kind = special.get(name)
            if kind == "symlink":
                os.symlink(f"/app/resources/patch_files/{hidden_name}", out)
            elif kind == "directory":
                out.mkdir()
            elif kind is None:
                out.write_bytes((directory / check / name).read_bytes())
            try:
                getattr(test_outputs, test)()
                verdict = "pass"
            except Exception:
                verdict = "fail"
            print(check, name, verdict)


def ours(directory: Path) -> None:
    sys.path.insert(0, os.getcwd())
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
    contexts = oracle.plan(Resources(), 0).artifact_contexts
    special = json.loads((directory / "special.json").read_text())
    for check, (path, _, _) in CHECKS.items():
        spec = FileSpec(path, Parser.TEXT, LIMIT)
        for name in names(directory, check):
            kind = special.get(name)
            read: FileRead
            if kind == "absent":
                read = FileStatus.ABSENT
            elif kind is not None:
                read = FileStatus.NOT_REGULAR
            else:
                data = (directory / check / name).read_bytes()
                read = FoundFile(data, hashlib.sha256(data).hexdigest(), False)
            evidence = ArtifactEvidence(check, (file_evidence(spec, read),), ())
            judgment = oracle.judge(check, contexts[check], evidence)
            print(check, name, "pass" if judgment.passed else "fail")


if __name__ == "__main__":
    command, target = sys.argv[1], Path(sys.argv[2])
    {"corpus": write_corpus, "native": native, "ours": ours}[command](target)
