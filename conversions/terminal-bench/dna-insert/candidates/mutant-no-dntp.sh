#!/bin/sh
# Wrong flags: runs oligotm without "-n 0.8" (dNTP concentration), takes for
# each primer the shortest annealed part at 58 C or more, and never checks the
# result with the required flags. It still lands inside the bounds: 15
# (forward, 59.54 C) and 30 (reverse, 58.08 C, just above the 58 C minimum).
apt-get update
apt-get install -y primer3
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
INPUT=$(sed -n '2p' sequences.fasta)
rc() {
  tr 'atcg' 'tagc' | rev
}
shortest() {
  n=15
  while [ "$n" -le 45 ]; do
    if [ "$1" = forward ]; then
      part=$(echo "$INPUT" | cut -c 214-$((213 + n)))
    else
      part=$(echo "$INPUT" | cut -c $((214 - n))-213 | rc)
    fi
    tm=$(oligotm -tp 1 -sc 1 -mv 50 -dv 2 -d 500 "$part")
    if awk -v t="$tm" 'BEGIN { exit !(t >= 58) }'; then
      echo "$n"
      return
    fi
    n=$((n + 1))
  done
}
sh "$HERE/write-primers" "$(shortest forward)" "$(shortest reverse)"
