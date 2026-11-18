#!/bin/sh
# Mutant: links pmars statically. It runs, but ldd reports "not a dynamic
# executable" on stderr and exits 1, which upstream's run_shell_command turns
# into a failure. Aimed at the emulation of check_output (exit status, empty output).
set -eu

echo 'deb-src http://deb.debian.org/debian stable main' >> /etc/apt/sources.list.d/deb-src.list
apt-get update
apt-get install -y --no-install-recommends build-essential libncurses-dev ca-certificates dpkg-dev

cd /app
apt-get source pmars
cd /app/pmars-*/src
sed -i 's/-DXWINGRAPHX//g' Makefile
sed -i 's/^LIB *=.*/LIB = -static -lncurses/' Makefile
make clean && make
install -m 0755 pmars /usr/local/bin/pmars
