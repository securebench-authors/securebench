#!/bin/sh
# Upstream's test.sh rebuilds the compiler from scratch with this exact chain and
# goes on to the testsuite whatever the build's exit status, so this setup
# always succeeds: a broken build fails the case, not the setup. The build log
# goes to a file because setup output is bounded.
cd /app/ocaml || exit 0
{ make clean && ./configure && make -j4; } > /tmp/securebench-build.log 2>&1
exit 0
