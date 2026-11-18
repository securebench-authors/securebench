#!/bin/sh
# Where the check is least like upstream's assertion: judge repeats text-mode
# open's universal newlines, readlines' line count and strip() itself. This
# mutant writes the right name with spaces and a tab around it and a Windows
# line ending, "  GritLM/GritLM-7B\t\r\n". Upstream accepts it (one line after
# universal newlines, and strip() removes the padding), so SecureBench must
# too.
# It fetches the results through sparse-fetch.inc (see there) and runs the
# reference's leaderboard.py with one change; it exits 1 without running
# anything if the change did not apply.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/sparse-fetch.inc" || exit 1
cd /app/results
sed -n "/^cat << 'EOF' > leaderboard.py$/,\$p" "$here/reference.sh" | sed 's|^    f.write(m)$|    f.write("  " + m + "\\t\\r\\n")|' > /tmp/mutant-leaderboard.sh
grep -q 'f.write("  " + m' /tmp/mutant-leaderboard.sh || exit 1
sh /tmp/mutant-leaderboard.sh
