#!/bin/sh
# The reference's primers followed by an empty line, as a here-document with a
# stray blank line before its terminator writes them. Upstream's test counts
# that line and requires exactly four.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
sh "$HERE/write-primers" 15 41
echo >> primers.fasta
