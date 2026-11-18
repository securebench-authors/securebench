#!/bin/sh
# Where the check is least like upstream's assertion: the artifact check
# decodes /app/result.txt as strict UTF-8 without a byte-order mark, where
# upstream opens it in text mode with the locale's encoding (UTF-8). This
# mutant writes the right name with encoding="utf-8-sig", as Windows tools
# expect, so the file starts with a byte-order mark. Upstream reads the mark as
# U+FEFF, which strip() keeps, so the equality fails; SecureBench must fail it
# too.
# It fetches the results through sparse-fetch.inc (see there) and runs the
# reference's leaderboard.py with one change; it exits 1 without running
# anything if the change did not apply.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
. "$here/sparse-fetch.inc" || exit 1
cd /app/results
sed -n "/^cat << 'EOF' > leaderboard.py$/,\$p" "$here/reference.sh" | sed 's|open("../result.txt", "w")|open("../result.txt", "w", encoding="utf-8-sig")|' > /tmp/mutant-leaderboard.sh
grep -q 'encoding="utf-8-sig"' /tmp/mutant-leaderboard.sh || exit 1
sh /tmp/mutant-leaderboard.sh
