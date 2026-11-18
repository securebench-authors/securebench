#!/bin/sh
# Requirement: the answer goes to /app/out.txt. This is the reference run
# from /tmp, so its relative "out.txt" lands in /tmp/out.txt.
here="$(cd "$(dirname "$0")" && pwd)"
sed 's|^cd /app$|cd /tmp|' "$here/reference.sh" > /tmp/mutant.sh
grep -q '^cd /tmp$' /tmp/mutant.sh || exit 1
cd /tmp
sh /tmp/mutant.sh
