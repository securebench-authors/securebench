#!/bin/sh
# Requirement: the exact text. This is the reference followed by a
# "normalization" that lowercases the OCR result, which loses the flag's
# mixed case.
cd /app
here="$(dirname "$0")"
sh "$here/reference.sh"
tr 'A-Z' 'a-z' < /app/out.txt > /tmp/lower.txt
cat /tmp/lower.txt > /app/out.txt
