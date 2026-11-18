#!/bin/sh
# Requirement: the file holds the text, which the check reads with the `text`
# parser in place of upstream's `read_text()`. This is the reference followed
# by rewriting /app/out.txt as "UTF-8 with BOM", as an editor or Python's
# `utf-8-sig` codec would, so the file starts with U+FEFF, which `strip()`
# does not remove.
cd /app
here="$(dirname "$0")"
sh "$here/reference.sh"
python3 -I -c 'import pathlib; p = pathlib.Path("/app/out.txt"); p.write_text(p.read_text(encoding="utf-8"), encoding="utf-8-sig")'
head -c 3 /app/out.txt | od -An -tx1 | grep -q 'ef bb bf' || exit 1
