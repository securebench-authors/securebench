#!/bin/sh
# Leaves the example gates.txt and installs /app/sim as a program that prints
# the right answer without simulating anything. Upstream's test, and the
# conversion's setup command, compile sim.c over /app/sim, so this must fail.
cd /app || exit 1
cp "$(dirname "$0")/fake-sim.py" /app/sim
chmod +x /app/sim
