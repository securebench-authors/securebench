#!/bin/sh
# Requirement: moves in the form [src][dst]. This is the reference writing
# each mate in standard algebraic notation (Qe4#, g4#) instead.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
sed -e 's/^        board.push(move)$/        san = board.san(move); board.push(move)/' \
    -e 's/^            best_moves.append(move.uci())$/            best_moves.append(san)/' \
    "$here/reference.sh" > /tmp/mutant.sh
grep -q 'san = board.san(move); board.push(move)' /tmp/mutant.sh || exit 1
grep -q 'best_moves.append(san)' /tmp/mutant.sh || exit 1
sh /tmp/mutant.sh
