#!/bin/sh
# Reads each word as a signed 32-bit integer, so words of 2^31 and above come
# out negative: probes the integer comparison of values reported by the adapter.
cd /app
sh "$(dirname "$0")/reference.sh"
sed -i 's/const word = data.readUInt32LE(i);/const word = data.readInt32LE(i);/' /app/extract.js
grep -q 'const word = data.readInt32LE(i);' /app/extract.js
