#!/bin/sh
# The reference primers, written in upper case and with classic Mac line
# endings (a lone CR, no LF). Upstream reads the file in Python text mode,
# whose universal newlines split on CR, and lower-cases each primer, so it
# passes. Aimed at the Oracle's line splitting and case handling, which
# replace Python's file iteration.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
cd /app
sh "$here/design-primers" /app/sequences.fasta \
  688-708 184-213 4-21 694-714 4-21 68-87 4-26 529-546 \
  | sed '/^>/!y/acgt/ACGT/' | tr '\n' '\r' > primers.fasta
