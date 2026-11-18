#!/bin/sh
# Aimed at the Oracle's two reimplemented length counts. The reference plus
# two pairs that write and then remove a lone-surrogate marker ("\ud800",
# which Python's json loads but SecureBench's strict JSON parser rejects) and
# one never-matching pair whose replacement is 1,200,000 "é" markers, which
# json.dump writes as é escapes (an escape-dense string that a scanner
# rescanning from each escape would take minutes over). All of it is written
# one pair per line with CRLF line endings and padded with spaces until the
# file has more than 10,000,000 bytes but, read in text mode (where each CRLF
# is one character), fewer than 10,000,000 characters. Its output equals the
# reference's, so both graders should pass it.
set -e
cd /app
sh "$(dirname "$0")/reference.sh"
python3 - <<'PY'
import json
pairs = json.load(open("/app/re.json"))
pairs += [["$", "\ud800"], ["\ud800", ""], ["(?!)", "é" * 1_200_000]]
body = "[" + ",\r\n".join(json.dumps(p) for p in pairs) + "\r\n]\r\n"
crlf = body.count("\r\n")
target = 10_000_000 + crlf // 2
assert len(body) < target
body = body[:1] + " " * (target - len(body)) + body[1:]
assert len(body) > 10_000_000 and len(body) - body.count("\r\n") < 10_000_000
assert "\\ud800" in body and "\\u00e9" * 1000 in body
open("/app/re.json", "w", newline="").write(body)
PY
