#!/bin/sh
# The reference, then two changes both graders should accept, each aimed at a
# normalization the conversion reimplements:
# - the secret rewritten with Unicode whitespace around it (no-break space, em
#   space, CRLF); upstream compares read_text().strip(), and the Oracle must
#   strip exactly the same characters;
# - a copy of the secret kept in a nested dot directory of the work tree;
#   upstream's checksum skips every path with a component starting with a dot.
# If the Oracle got either wrong, SecureBench would fail what native passes.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app/repo || exit 1
mkdir -p .recovered/notes
cp /app/secret.txt .recovered/notes/secret.txt
printf '\302\240 secret[lost_and_found_in_git]\r\n\342\200\203\n' > /app/secret.txt
