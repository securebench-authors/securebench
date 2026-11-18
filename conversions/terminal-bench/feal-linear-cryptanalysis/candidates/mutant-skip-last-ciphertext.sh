#!/bin/sh
# The reference with an off-by-one: it recovers the right key but decrypts
# only the first 99 of the 100 ciphertexts.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -q '"./decrypt ciphertexts.txt ' "$here/reference.sh" || exit 1
sed 's|"./decrypt ciphertexts.txt |"head -n 99 ciphertexts.txt > first.txt \&\& ./decrypt first.txt |' "$here/reference.sh" | sh
