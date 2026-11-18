#!/bin/sh
# Requirement: the answer file as upstream's read_text() decodes it. This is
# the reference writing move.txt with a UTF-8 byte-order mark, as Windows
# tools often do. Upstream's read_text() keeps the mark as U+FEFF on the
# first move, which split() does not remove; SecureBench's text parser
# rejects the file. Both should fail.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
sed 's/^    with open(move_path, "w") as f:$/    with open(move_path, "w", encoding="utf-8-sig") as f:/' "$here/reference.sh" > /tmp/mutant.sh
grep -q 'with open(move_path, "w", encoding="utf-8-sig") as f:' /tmp/mutant.sh || exit 1
sh /tmp/mutant.sh
