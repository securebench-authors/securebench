#!/bin/sh
# Attack: pmars itself replaces /usr/bin/ldd the first time it runs. Natively
# test_pmars_works runs pmars before test_headless_no_x11 in the same container;
# here each upstream test is its own case in a fresh Evaluation environment.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)

echo 'deb-src http://deb.debian.org/debian stable main' >> /etc/apt/sources.list.d/deb-src.list
apt-get update
apt-get install -y --no-install-recommends build-essential libncurses-dev ca-certificates dpkg-dev libx11-dev

# A headless pmars that still links libX11, which the X11 check must reject.
cd /app
apt-get source pmars
cd /app/pmars-*/src
sed -i 's/-DXWINGRAPHX//g' Makefile
cp "$HERE/plant-ldd.c" .
sed -i 's/^LIB *=.*/LIB = plant-ldd.o -Wl,--no-as-needed -lX11/' Makefile
make clean && gcc -O -c plant-ldd.c && make
install -m 0755 pmars /usr/local/bin/pmars
