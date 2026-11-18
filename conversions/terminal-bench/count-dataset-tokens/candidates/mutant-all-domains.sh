#!/bin/sh
# The reference, but without the domain filter, so it counts the whole dataset
# (math, code and puzzle as well as science).
here=$(cd "$(dirname "$0")" && pwd)
cd /app
line='ds = ds.filter(lambda x: x["domain"] in ["chemistry", "biology", "physics"])'
grep -qxF "$line" "$here/reference.sh" || exit 1
grep -vxF "$line" "$here/reference.sh" | sh
