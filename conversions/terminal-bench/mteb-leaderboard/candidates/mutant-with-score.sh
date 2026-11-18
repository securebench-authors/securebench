#!/bin/sh
# Requirement: result.txt holds the name, one line. This mutant also writes
# the winning score on a second line, as its own log line reports it.
# It fetches the results through sparse-fetch.inc (see there) and runs the
# reference's leaderboard.py with one change; it exits 1 without running
# anything if the change did not apply.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/sparse-fetch.inc" || exit 1
cd /app/results
sed -n "/^cat << 'EOF' > leaderboard.py$/,\$p" "$here/reference.sh" | sed 's|^    f.write(m)$|    f.write(m + "\\n" + str(model_avgs[m]) + "\\n")|' > /tmp/mutant-leaderboard.sh
grep -q 'str(model_avgs\[m\])' /tmp/mutant-leaderboard.sh || exit 1
sh /tmp/mutant-leaderboard.sh
