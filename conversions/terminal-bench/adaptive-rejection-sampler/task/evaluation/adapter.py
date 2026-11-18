"""adaptive-rejection-sampler adapter: run one upstream R test's code, report what happened.

Assertion-free. Each mode runs the candidate's /app/ars.R under the R that the
check's setup restored (setup.py), from /app as upstream does, and reports how
the run ended, its output and what ars returned. The Oracle decides.

The R test scripts that make upstream's calls arrive in the challenge
(`script`), never from evaluation/, because their densities, domains and
counts decide what the Oracle accepts. The adapter writes the script to its
own temporary directory and runs it with Rscript, as it ran the same file from
evaluation/ before.

- generate: the challenge's script (test_can_generate_standard_distribution_
  samples); the samples ars returned.
- validation: the challenge's script (test_input_validation_functionality);
  for each call, error or returned.
- log-concavity: the challenge's script (test_log_concavity_functionality);
  error or returned, and the run's output.
- formal-testing: the challenge's script (the generate check's), then
  upstream's own run_test.R, in upstream's order; the output of run_test.R.
  The sample files are collected after it as Output Artifacts.
- test-function: no R and an empty challenge; the text of each /app/*.R, as
  upstream's glob reads it.
"""

import json
import math
import os
import signal
import struct
import subprocess
import sys
import tempfile

EVALUATION = "/.securebench/evaluation"
RSCRIPT = "/usr/bin/Rscript"
# Upstream's subprocess timeouts for each R script.
TIMEOUTS = {"generate": 30, "validation": 15, "log-concavity": 15, "formal-testing": 60}
SHOWN = 16384
MAX_SAMPLES = 100_000
MAX_R_FILES = 8
MAX_R_TEXT = 65536
MAX_R_READ = 64 << 20


def stream(data: bytes) -> dict[str, object]:
    """Output as upstream's text=True sees it: whole when short, else its two ends."""
    try:
        data.decode("utf-8")
        valid = True
    except UnicodeDecodeError:
        valid = False
    if len(data) <= 2 * SHOWN:
        head, tail = data, b""
    else:
        head, tail = data[:SHOWN], data[-SHOWN:]
    return {
        "bytes": len(data),
        "utf8": valid,
        "head": head.decode("utf-8", "replace"),
        "tail": tail.decode("utf-8", "replace"),
    }


def run_r(script: str, arguments: list[str], timeout: int) -> dict[str, object]:
    process = subprocess.Popen(
        [RSCRIPT, script, *arguments],
        cwd="/app",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        out, err = process.communicate(timeout=timeout)
        ending, status = "exited", max(-255, min(255, process.returncode))
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        out, err = process.communicate()
        ending, status = "timed_out", 0
    return {"ending": ending, "exit_status": status, "stdout": stream(out), "stderr": stream(err)}


def read_word(path: str, words: tuple[str, ...]) -> str:
    """The one word a driver wrote to `path`: one of `words`, absent or unrecognised."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(64)
    except FileNotFoundError:
        return "absent"
    word = data.decode("utf-8", "replace").strip()
    return word if word in words else "unrecognised"


def write_script(record: str, name: str, script: str) -> str:
    """Write the challenge's R test script beside the record, where Rscript runs it."""
    path = os.path.join(os.path.dirname(record), name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(script)
    return path


def generate(record: str, script: str) -> dict[str, object]:
    run = run_r(write_script(record, "generate.R", script), [record], TIMEOUTS["generate"])
    outcome = read_word(record + ".outcome", ("returned", "error", "not-numeric"))
    count, non_finite, values = 0, 0, []
    if outcome == "returned":
        try:
            size = os.path.getsize(record + ".bin")
        except OSError:
            size = -1
        if size < 0 or size % 8 != 0:
            outcome = "unrecognised"
        else:
            count = size // 8
            if count <= MAX_SAMPLES:
                with open(record + ".bin", "rb") as handle:
                    data = handle.read(size)
                for value in struct.unpack(f"<{count}d", data):
                    if math.isfinite(value):
                        values.append(value)
                    else:
                        non_finite += 1
    return {
        "run": run,
        "outcome": outcome,
        "count": count,
        "non_finite": non_finite,
        "values": values,
    }


def validation(record: str, script: str) -> dict[str, object]:
    run = run_r(write_script(record, "validation.R", script), [record], TIMEOUTS["validation"])
    try:
        with open(record, "rb") as handle:
            lines = handle.read(64).decode("utf-8", "replace").split("\n")[:2]
    except FileNotFoundError:
        lines = []
    outcomes = [line if line in ("returned", "error") else "unrecognised" for line in lines if line]
    return {"run": run, "outcomes": outcomes}


def log_concavity(record: str, script: str) -> dict[str, object]:
    run = run_r(write_script(record, "logconcave.R", script), [record], TIMEOUTS["log-concavity"])
    return {"run": run, "outcome": read_word(record, ("returned", "error"))}


def formal_testing(record: str, script: str) -> dict[str, object]:
    # Upstream runs its sampling script before test(), in the same container,
    # and reads the sample files after both. Its result is the generate check's
    # business; here it only leaves /app as upstream's later tests find it.
    run_r(write_script(record, "generate.R", script), [record], TIMEOUTS["generate"])
    return {"run": run_r(f"{EVALUATION}/run_test.R", [], TIMEOUTS["formal-testing"])}


def r_file(name: str) -> dict[str, object]:
    """One /app/*.R entry as `Path.read_text()` would read it: through links, strict UTF-8."""
    shown = name.encode("utf-8", "surrogateescape").decode("utf-8", "replace")
    path = os.path.join("/app", name)
    entry: dict[str, object] = {"name": shown, "kind": "other", "bytes": 0, "utf8": False, "text": ""}
    if not os.path.isfile(path):
        return entry
    with open(path, "rb") as handle:
        data = handle.read(MAX_R_READ + 1)
    entry.update(kind="file", bytes=len(data))
    if len(data) <= MAX_R_READ:
        try:
            data.decode("utf-8")
            entry["utf8"] = True
        except UnicodeDecodeError:
            pass
        entry["text"] = data[:MAX_R_TEXT].decode("utf-8", "replace")
    return entry


def test_function() -> dict[str, object]:
    names = sorted(
        (name for name in os.listdir("/app") if name.endswith(".R")),
        key=lambda name: (name != "ars.R", name.encode("utf-8", "surrogateescape")),
    )
    return {"count": len(names), "files": [r_file(name) for name in names[:MAX_R_FILES]]}


def main() -> None:
    mode = sys.argv[1]
    challenge = json.loads(sys.stdin.buffer.read())
    record = os.path.join(tempfile.mkdtemp(prefix="securebench-"), "record")
    if mode == "generate":
        observation = generate(record, challenge["script"])
    elif mode == "validation":
        observation = validation(record, challenge["script"])
    elif mode == "log-concavity":
        observation = log_concavity(record, challenge["script"])
    elif mode == "formal-testing":
        observation = formal_testing(record, challenge["script"])
    else:
        observation = test_function()
    sys.stdout.write(json.dumps({"observation": observation}, ensure_ascii=False))


main()
