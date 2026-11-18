#!/bin/sh
# Requirement: the position shown in the image. This is the reference reading
# the files right to left (the h-file as column 0), so it solves the mirrored
# position and writes its mates.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
sed 's/^            board\[row\]\[col\] = best_piece$/            board[row][7 - col] = best_piece/' "$here/reference.sh" > /tmp/mutant.sh
grep -q 'board\[row\]\[7 - col\] = best_piece' /tmp/mutant.sh || exit 1
sh /tmp/mutant.sh
