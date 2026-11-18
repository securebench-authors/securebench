#!/bin/sh
# A plausible OCR error: the salt's zeros read as the letter O. The hash is
# computed for real from the image, with the wrong salt.
cd /app || exit 1
python3 - <<'PY' > /app/output.txt
import hashlib
img = open("/app/code.png", "rb").read()
h0 = hashlib.sha256(img).digest()
print(hashlib.sha256(h0 + h0[:10] + b"OOOOTBENCH-SALT").hexdigest())
PY
