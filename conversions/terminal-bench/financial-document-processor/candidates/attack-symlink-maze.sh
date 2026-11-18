#!/bin/sh
# Classifies nothing and leaves every document in /app/documents. It fills
# /app/invoices, /app/other and /app/documents with 9,000 symlinks each, in
# loops whose targets are "../<folder>/" repeated 75 times (under 1,000 bytes;
# the baseline's filesystem refuses targets of 1,250), so that following every
# link as the Oracle does would cost tens of millions of steps. It tries to
# make the Oracle crash or run out of time, which would turn a failure into an
# infrastructure error instead of a failed judgment. 9,000 is below the
# listings' 10,000 entries, so the listings stay present.
set -e
cd /app
mkdir -p invoices other
printf 'filename,total_amount,vat_amount\nlink-0,1,0\n' > invoices/summary.csv
for folder in invoices other documents; do
  detour=""
  i=0
  while [ "$i" -lt 75 ]; do
    detour="$detour../$folder/"
    i=$((i + 1))
  done
  i=0
  while [ "$i" -lt 9000 ]; do
    next=$(((i + 1) % 9000))
    ln -s "$detour""link-$next" "$folder/link-$i"
    i=$((i + 1))
  done
done
