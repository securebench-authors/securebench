#!/bin/sh
# Requirement: the highest Mean (Task), which the leaderboard computes only for
# models with a score on every task of the benchmark. This mutant considers
# every model in the repository and averages each over the tasks it has
# scores for, so a model evaluated on a few easy tasks wins.
# It fetches the results through sparse-fetch.inc (see there) and runs the
# reference's leaderboard.py with one change; it exits 1 without running
# anything if the change did not apply.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/sparse-fetch.inc" || exit 1
cd /app/results
sed -n "/^cat << 'EOF' > leaderboard.py$/,\$p" "$here/reference.sh" | sed -e 's/, tasks=tasks, models=models)/, tasks=tasks)/' -e 's/^df_full = df_scores.dropna(axis=1, how="any")$/df_full = df_scores/' > /tmp/mutant-leaderboard.sh
grep -q '^df_full = df_scores$' /tmp/mutant-leaderboard.sh || exit 1
grep -q 'models=models)' /tmp/mutant-leaderboard.sh && exit 1
sh /tmp/mutant-leaderboard.sh
