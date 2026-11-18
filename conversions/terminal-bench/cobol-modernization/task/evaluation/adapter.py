"""Adapter for cobol-modernization: replays upstream's test_outputs.py steps.

It records which required files exist, writes the initial data files, runs
/app/program.py once per input exactly as the upstream test does, and reports
for each run its exit status and whether its standard output and error decode
as UTF-8. The resulting data files are collected by SecureBench as Output
Artifacts; the Oracle compares them with upstream's expected contents.
"""

import codecs
import json
import subprocess
import sys
import threading
from pathlib import Path

# The baseline's interpreter. Upstream's test runs `python` from the PATH of a
# uv tool environment whose base interpreter is this same /usr/local Python.
PYTHON = "/usr/local/bin/python"

DATA = Path("/app/data")
INPUT = Path("/app/src/INPUT.DAT")


def unable(code: str, message: str) -> None:
    json.dump({"unable": {"code": code, "message": message[:4000]}}, sys.stdout)
    sys.exit(0)


class Utf8Check:
    """Reads a pipe to its end and records whether it decodes as strict UTF-8.

    Upstream runs the program with capture_output=True and text=True, so
    subprocess decodes both streams with the locale encoding (UTF-8 in the
    baseline) and strict errors once the program has exited, and a decode
    error fails the test. The incremental decoder gives the same answer as
    decoding the whole output, without holding it in memory.
    """

    def __init__(self, pipe) -> None:
        self.pipe = pipe
        self.valid = True
        self.thread = threading.Thread(target=self.read)
        self.thread.start()

    def read(self) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")("strict")
        while True:
            chunk = self.pipe.read(65536)
            if self.valid:
                try:
                    decoder.decode(chunk, final=not chunk)
                except UnicodeDecodeError:
                    self.valid = False
            if not chunk:
                break
        self.pipe.close()


def main() -> None:
    challenge = json.load(sys.stdin)

    # test_required_files_exist and test_data_files_exist use Path.exists.
    existed = {
        "program_py": Path("/app/program.py").exists(),
        "accounts_dat": (DATA / "ACCOUNTS.DAT").exists(),
        "books_dat": (DATA / "BOOKS.DAT").exists(),
        "transactions_dat": (DATA / "TRANSACTIONS.DAT").exists(),
        "input_dat": INPUT.exists(),
    }

    initial = challenge["initial"]
    try:
        (DATA / "ACCOUNTS.DAT").write_text(initial["accounts"], encoding="utf-8")
        (DATA / "BOOKS.DAT").write_text(initial["books"], encoding="utf-8")
        (DATA / "TRANSACTIONS.DAT").write_text(initial["transactions"], encoding="utf-8")
    except OSError as error:
        unable("write-data", f"could not write the initial data files: {error}")

    runs = []
    for line in challenge["inputs"]:
        try:
            INPUT.write_text(line, encoding="utf-8")
        except OSError as error:
            unable("write-input", f"could not write INPUT.DAT: {error}")
        try:
            process = subprocess.Popen(
                [PYTHON, "/app/program.py"],
                cwd="/app",
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as error:
            unable("run", f"could not start {PYTHON}: {error}")
        stdout = Utf8Check(process.stdout)
        stderr = Utf8Check(process.stderr)
        stdout.thread.join()
        stderr.thread.join()
        returncode = process.wait()
        runs.append({"returncode": returncode, "stdout_utf8": stdout.valid, "stderr_utf8": stderr.valid})
        # Upstream's test stops at the first run whose output does not decode
        # or whose return code is not 0.
        if returncode != 0 or not stdout.valid or not stderr.valid:
            break

    json.dump({"observation": {"existed": existed, "runs": runs}}, sys.stdout)


if __name__ == "__main__":
    main()
