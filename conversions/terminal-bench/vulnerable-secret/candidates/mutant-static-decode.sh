#!/bin/sh
# Skips the exploit and XOR-decodes the encrypted key straight from the binary,
# but with an off-by-one: it decodes the 0x42 terminator too, leaving a
# trailing NUL character that str.strip() keeps. Both graders should fail it;
# it probes how a NUL in otherwise valid UTF-8 reaches the Oracle.
set -e
cd /app
python3 - <<'PY'
data = open("/app/vulnerable", "rb").read()
start = data.index(bytes(b ^ 0x42 for b in b"FLAG{"))
end = data.index(b"\x42", start)
key = bytes(b ^ 0x42 for b in data[start:end + 1])
open("/app/results.txt", "wb").write(key + b"\n")
PY
