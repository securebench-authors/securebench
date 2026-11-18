#!/bin/sh
# The upstream solution, kept byte for byte in upstream/solve.sh and run from /app
# with bash, as its shebang asks. It writes vm.js and make_json.js to the current
# directory and runs `node make_json.js doomgeneric_mips > memory.js`.
cd /app
exec bash "$(dirname "$0")/upstream/solve.sh"
