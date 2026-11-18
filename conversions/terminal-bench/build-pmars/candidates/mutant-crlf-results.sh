#!/bin/sh
# Mutant: ends the results line with CRLF. Upstream decodes with universal
# newlines and strips, so this passes natively. Aimed at the Oracle's
# emulation of decoding, newline translation and the "Results:" match.
set -eu

echo 'deb-src http://deb.debian.org/debian stable main' >> /etc/apt/sources.list.d/deb-src.list
apt-get update
apt-get install -y --no-install-recommends build-essential libncurses-dev ca-certificates dpkg-dev

cd /app
apt-get source pmars
cd /app/pmars-*/src
sed -i 's/-DXWINGRAPHX//g' Makefile
sed -i 's/^LIB *=.*/LIB = -lncurses/' Makefile
sed -i 's|^char   \*resultsWLT = "Results: %d %d %d\\n";|char   *resultsWLT = "Results: %d %d %d\\r\\n";|' str_eng.c
grep -q 'Results: %d %d %d\\r\\n' str_eng.c
make clean && make
install -m 0755 pmars /usr/local/bin/pmars
