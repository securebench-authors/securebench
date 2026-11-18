#!/bin/sh
# The reference without its search for the last round key: the linear attack
# recovers round keys 0 to 2, round key 3 stays 0, and every ciphertext is
# decrypted with a wrong final round.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -qx '  brute_force_last();' "$here/reference.sh" || exit 1
sed 's|^  brute_force_last();$|  /* last round key not searched */|' "$here/reference.sh" | sh
