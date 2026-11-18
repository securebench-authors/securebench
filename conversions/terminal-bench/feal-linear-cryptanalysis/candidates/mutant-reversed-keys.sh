#!/bin/sh
# The reference, but it passes the recovered keys to ./decrypt in reverse
# order (k3, k2, k1, k0), confusing the round order of decryption.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -q '0x%x", k0, k1, k2, k3);' "$here/reference.sh" || exit 1
sed 's|0x%x", k0, k1, k2, k3);|0x%x", k3, k2, k1, k0);|' "$here/reference.sh" | sh
