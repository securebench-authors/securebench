#!/bin/sh
# Requirement: one move per line. This is the reference joining the moves
# with commas on a single line.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
sed 's/^        f.write("\\n".join(best_moves))$/        f.write(",".join(best_moves))/' "$here/reference.sh" > /tmp/mutant.sh
grep -q 'f.write(",".join(best_moves))' /tmp/mutant.sh || exit 1
sh /tmp/mutant.sh
