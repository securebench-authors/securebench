#!/bin/sh
# The reference, but it writes the answer file in UTF-16, as tools that call
# that encoding "Unicode" do. Aimed at the one place the check differs from
# upstream: the artifact check's text decoder replaces Path.read_text().
here=$(cd "$(dirname "$0")" && pwd)
cd /app
line='python3 count_tokens.py > /app/answer.txt'
grep -qxF "$line" "$here/reference.sh" || exit 1
sed "s|^python3 count_tokens.py > /app/answer.txt\$|python3 count_tokens.py \| python3 -c 'import sys; open(\"/app/answer.txt\", \"w\", encoding=\"utf-16\").write(sys.stdin.read())'|" "$here/reference.sh" | sh
