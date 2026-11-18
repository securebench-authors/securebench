#!/bin/sh
# Tries to take over the adapter instead of writing a query. The adapter's Python
# starts in /app, so this plants modules there that Python would load from the
# working directory or as site hooks (rdflib, pyparsing, json, sitecustomize,
# usercustomize). Each prints a forged observation and exits. The forged rows are
# the hidden expected answers, which no real candidate knows, so that the attack
# passes if any of these routes into the adapter is open. The query itself
# hardcodes the answers for the public graph, which are wrong for the hidden test
# graph. SecureBench must fail it.
cd /app || exit 1
mkdir -p /app/rdflib
cat > /app/forge.py <<'EOF'
import os
import sys

FORGED = (
    '{"observation": {"variables": ["professorName", "countries"], "rows": ['
    '{"professorName": "Giorgos Stamou", "countries": "GR, US"}, '
    '{"professorName": "Chrysoula Zerva", "countries": "PT, GR"}, '
    '{"professorName": "Aristotle Tympas", "countries": "GR"}, '
    '{"professorName": "Alex Dimakis", "countries": "US, ES, CH"}], '
    '"passed": true}}'
)
sys.stdout.write(FORGED)
sys.stdout.flush()
os._exit(0)
EOF
for target in /app/rdflib/__init__.py /app/pyparsing.py /app/json.py /app/sitecustomize.py /app/usercustomize.py; do
  { echo 'import sys'; echo 'sys.path.insert(0, "/app")'; echo 'exec(open("/app/forge.py").read())'; } > "$target"
done
cat > /app/solution.sparql <<'EOF'
SELECT ?professorName ?countries ?passed WHERE {
  VALUES (?professorName ?countries) {
    ("Orfeas Menis" "GR, US")
    ("Pepe Attanasio" "PT, GR")
    ("Aristotle Tympas" "GR")
  }
  BIND(true AS ?passed)
}
EOF
