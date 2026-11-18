#!/bin/sh
# Mutant: the debugger quits on the first command it cannot parse. Under
# /bin/sh (dash), upstream's `echo -e` sends "-e s" as the first command, so
# only the first address is printed. Aimed at the standard input the adapter
# gives pmars and at the reimplemented address count, at its threshold.
set -eu

echo 'deb-src http://deb.debian.org/debian stable main' >> /etc/apt/sources.list.d/deb-src.list
apt-get update
apt-get install -y --no-install-recommends build-essential libncurses-dev ca-certificates dpkg-dev

cd /app
apt-get source pmars
cd /app/pmars-*/src
sed -i 's/-DXWINGRAPHX//g' Makefile
sed -i 's/^LIB *=.*/LIB = -lncurses/' Makefile
sed -i '/^bad_arg(argStr)/,/^}/ s/cdb_fputs(outs, FORCE);/cdb_fputs(outs, FORCE); Exit(USERABORT);/' cdb.c
grep -q 'Exit(USERABORT);' cdb.c
make clean && make
install -m 0755 pmars /usr/local/bin/pmars
