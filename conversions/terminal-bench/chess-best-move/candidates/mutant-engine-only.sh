#!/bin/sh
# Requirement: every winning move. This is the reference without its
# mate-in-one shortcut, so it trusts Stockfish's single best move and writes
# one of the two mates.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
sed 's/^    if best_moves:$/    if False:/' "$here/reference.sh" > /tmp/mutant.sh
grep -q '^    if False:$' /tmp/mutant.sh || exit 1
sh /tmp/mutant.sh
