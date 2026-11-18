#!/bin/sh
# Runs the real exploit and writes the flag with Python's "utf-8-sig" codec,
# which prefixes a byte-order mark. Upstream reads the file as plain UTF-8,
# keeps U+FEFF (str.strip() does not remove it) and fails; SecureBench's text
# parser rejects a BOM. Both should fail.
set -e
cd /app
secret=$(sh "$(dirname "$0")/exploit-secret")
SECRET="$secret" python3 -c 'import os; open("/app/results.txt", "w", encoding="utf-8-sig").write(os.environ["SECRET"] + "\n")'
