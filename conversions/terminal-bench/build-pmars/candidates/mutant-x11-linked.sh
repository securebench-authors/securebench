#!/bin/sh
# Mutant: a headless build that still links libX11 (as-needed linking is
# turned off). Aimed at the X11 check: ldd runs on libraries captured from
# /usr/lib/x86_64-linux-gnu, and the Oracle does the substring test.
set -eu

echo 'deb-src http://deb.debian.org/debian stable main' >> /etc/apt/sources.list.d/deb-src.list
apt-get update
apt-get install -y --no-install-recommends build-essential libncurses-dev ca-certificates dpkg-dev
apt-get install -y --no-install-recommends libx11-dev

cd /app
apt-get source pmars
cd /app/pmars-*/src
sed -i 's/-DXWINGRAPHX//g' Makefile
sed -i 's/^LIB *=.*/LIB = -Wl,--no-as-needed -lX11/' Makefile
make clean && make
install -m 0755 pmars /usr/local/bin/pmars
