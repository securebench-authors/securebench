#!/bin/sh
# The same noisy OCR transcript as mutant-ocr-tie.sh with one more "e" misread:
# distance 136 over 1,350 characters, just below upstream's 90 percent.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
sh "$here/reference.sh" || exit 1
perl -pi -e 's/e/$n++ < 132 ? "c" : "e"/ge' /app/solution.txt
printf 'inv\n' >> /app/solution.txt
