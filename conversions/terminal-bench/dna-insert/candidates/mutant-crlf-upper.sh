#!/bin/sh
# The reference's primers, written in upper case with Windows line endings and
# trailing spaces. Upstream's test lower-cases the primers and reads the file
# with universal newlines and rstrip, so this passes natively.
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
sh "$HERE/write-primers" 15 41
tr 'a-z' 'A-Z' < primers.fasta | sed 's/$/  \r/' > primers.tmp
mv primers.tmp primers.fasta
