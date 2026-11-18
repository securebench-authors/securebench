#!/bin/sh
# The right hash, written with a UTF-8 byte-order mark, as Windows-minded code
# does. Upstream reads the file as plain UTF-8, keeps the mark and fails the
# comparison; SecureBench's text parser rejects the mark. Aimed at the
# difference between the two decoders.
cd /app || exit 1
python3 - <<'PY'
import hashlib
img = open("/app/code.png", "rb").read()
h0 = hashlib.sha256(img).digest()
digest = hashlib.sha256(h0 + h0[:10] + b"0000TBENCH-SALT").hexdigest()
with open("/app/output.txt", "w", encoding="utf-8-sig") as f:
    f.write(digest + "\n")
PY
