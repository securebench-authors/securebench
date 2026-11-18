#!/bin/sh
# The right hash, written with surrounding whitespace upstream's str.strip()
# removes: spaces, a tab, a no-break space, an ideographic space and CRLF.
# Aimed at the Oracle's reimplementation of upstream's normalization; both
# graders should pass it.
cd /app || exit 1
python3 - <<'PY'
import hashlib
img = open("/app/code.png", "rb").read()
h0 = hashlib.sha256(img).digest()
digest = hashlib.sha256(h0 + h0[:10] + b"0000TBENCH-SALT").hexdigest()
with open("/app/output.txt", "w", encoding="utf-8", newline="") as f:
    f.write("  \t 　" + digest + " \r\n\r\n")
PY
