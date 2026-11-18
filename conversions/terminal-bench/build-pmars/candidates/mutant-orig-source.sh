#!/bin/sh
# Mutant: builds from the upstream tarball alone, so /app/pmars-0.9.4 has no
# debian/ directory. Aimed at the glob and existence probes the adapter makes.
set -eu

echo 'deb-src http://deb.debian.org/debian stable main' >> /etc/apt/sources.list.d/deb-src.list
apt-get update
apt-get install -y --no-install-recommends build-essential libncurses-dev ca-certificates dpkg-dev

cd /app
apt-get source --download-only pmars
tar xf pmars_0.9.4.orig.tar.xz
cd /app/pmars-0.9.4/src
sed -i 's/-DXWINGRAPHX//g' Makefile
sed -i 's/^LIB *=.*/LIB = -lncurses/' Makefile
make clean && make
install -m 0755 pmars /usr/local/bin/pmars
