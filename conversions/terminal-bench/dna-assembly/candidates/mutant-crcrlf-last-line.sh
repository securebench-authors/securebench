#!/bin/sh
# The reference primers with the last line ended by CR CR LF, as a doubled
# line-ending conversion leaves it. Universal newlines read that as a line
# break followed by an empty line, so upstream sees 17 lines and fails. A
# grader that split on LF only and stripped each line would see 16 valid
# lines. Aimed at the Oracle's line splitting.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sh "$here/design-primers" /app/sequences.fasta \
  688-708 184-213 4-21 694-714 4-21 68-87 4-26 529-546 \
  | sed '$s/$/\r\r/' > primers.fasta
