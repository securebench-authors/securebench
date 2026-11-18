#!/bin/sh
# A noisy OCR transcript: the first 131 letters "e" read as "c", and a stray
# last line "inv". The file is 1,350 characters at Levenshtein distance 135,
# exactly 10 percent, so upstream's similarity is exactly at its 90 percent
# threshold. Upstream accepts with >=; the Oracle must round the same way.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
sh "$here/reference.sh" || exit 1
perl -pi -e 's/e/$n++ < 131 ? "c" : "e"/ge' /app/solution.txt
printf 'inv\n' >> /app/solution.txt
