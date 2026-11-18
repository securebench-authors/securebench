#!/bin/sh
# Wrong: estimates Tm with the Wallace rule (2 C per A/T, 4 C per G/C) instead
# of oligotm, and takes for each primer the shortest annealed part estimated at
# 58 C or more: 18 (forward) and 23 (reverse) nucleotides. The reverse part's
# oligotm Tm is 52.19 C, below the 58 C minimum.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
INPUT=$(sed -n '2p' sequences.fasta)
shortest() {
  awk -v s="$INPUT" -v strand="$1" 'BEGIN {
    for (n = 15; n <= 45; n++) {
      part = (strand == "forward") ? substr(s, 214, n) : substr(s, 214 - n, n)
      gc = gsub(/[gc]/, "", part)
      if (2 * (n - gc) + 4 * gc >= 58) { print n; exit }
    }
  }'
}
sh "$HERE/write-primers" "$(shortest forward)" "$(shortest reverse)"
