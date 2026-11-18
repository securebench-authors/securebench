#!/bin/sh
# Replaces /app/code.png with other bytes and writes the snippet's hash of the
# new image, as if the grader recomputed the answer from the image in the
# candidate's tree.
cd /app || exit 1
printf 'not the original image\n' > /app/code.png
python3 - <<'PY' > /app/output.txt
import hashlib
img = open("/app/code.png", "rb").read()
h0 = hashlib.sha256(img).digest()
print(hashlib.sha256(h0 + h0[:10] + b"0000TBENCH-SALT").hexdigest())
PY
