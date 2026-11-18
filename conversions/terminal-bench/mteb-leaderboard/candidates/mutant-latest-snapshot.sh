#!/bin/sh
# Requirement: the leaderboard as of August 2025. This mutant ranks the models
# on a later state of the results repository instead: commit
# b4c3f20fad9749807d3aa2222393d056cb3d9d4f (2 July 2026), the head of its main
# branch when we wrote it, pinned so that the mutant's output does not move
# with the repository.
# It fetches the results through sparse-fetch.inc (see there) with only the
# commit changed, and runs the reference's leaderboard.py unchanged; it exits 1
# without running anything if the change did not apply.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
sed 's/^commit=c0fd3271442f8c0c839084a109fede85c8514dab$/commit=b4c3f20fad9749807d3aa2222393d056cb3d9d4f/' "$here/sparse-fetch.inc" > /tmp/mutant-fetch.inc
grep -q '^commit=b4c3f20fad9749807d3aa2222393d056cb3d9d4f$' /tmp/mutant-fetch.inc || exit 1
. /tmp/mutant-fetch.inc || exit 1
cd /app/results
sed -n "/^cat << 'EOF' > leaderboard.py$/,\$p" "$here/reference.sh" > /tmp/mutant-leaderboard.sh
sh /tmp/mutant-leaderboard.sh
