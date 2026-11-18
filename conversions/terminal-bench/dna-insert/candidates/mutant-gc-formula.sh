#!/bin/sh
# Wrong: estimates Tm with the basic GC-content formula
# (64.9 + 41 * (GC - 16.4) / N) instead of oligotm, and takes for each primer
# the shortest annealed part estimated at 58 C or more. That gives 21 (forward)
# and 44 (reverse) nucleotides, whose oligotm Tm values are 68.71 and 63.17 C:
# 5.54 C apart, just over the 5 C limit.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
INPUT=$(sed -n '2p' sequences.fasta)
shortest() {
  # $1: forward or reverse
  awk -v s="$INPUT" -v strand="$1" 'BEGIN {
    for (n = 15; n <= 45; n++) {
      part = (strand == "forward") ? substr(s, 214, n) : substr(s, 214 - n, n)
      gc = gsub(/[gc]/, "", part)
      if (64.9 + 41 * (gc - 16.4) / n >= 58) { print n; exit }
    }
  }'
}
sh "$HERE/write-primers" "$(shortest forward)" "$(shortest reverse)"
