#!/bin/sh
# The right hash in upper-case hex. Upstream compares exactly, so this fails;
# aimed at the Oracle's comparison, which must not fold case.
cd /app || exit 1
python3 - <<'PY' > /app/output.txt
import hashlib
img = open("/app/code.png", "rb").read()
h0 = hashlib.sha256(img).digest()
print(hashlib.sha256(h0 + h0[:10] + b"0000TBENCH-SALT").hexdigest().upper())
PY
