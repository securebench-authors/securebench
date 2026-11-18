#!/bin/sh
# Makes /app/extract.js a directory holding index.js. `node /app/extract.js`
# still runs it and prints the right memory map, but upstream's
# test_extract_js_exists requires a file: probes the conversion's file check.
cd /app
sh "$(dirname "$0")/reference.sh"
mv /app/extract.js /app/index.js.tmp
mkdir /app/extract.js
mv /app/index.js.tmp /app/extract.js/index.js
