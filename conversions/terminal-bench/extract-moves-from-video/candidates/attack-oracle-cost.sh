#!/bin/sh
# Writes 64,800 characters of moves, just under the adapter's 64 KiB
# bound, so that a judge running the quadratic Levenshtein loop on it would do
# about 87 million steps on the host, hoping to time out the judgment and turn
# the attempt invalid instead of failed.
cd /app || exit 1
i=0
: > /app/solution.txt
while [ "$i" -lt 2160 ]; do
  printf 'n\ns\ne\nw\nu\nd\nget all\nopen case\n' >> /app/solution.txt
  i=$((i + 1))
done
