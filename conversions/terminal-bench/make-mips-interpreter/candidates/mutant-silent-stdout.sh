#!/bin/sh
# The reference with write(2) implemented only for files the program opened:
# writes to stdout and stderr report success but print nothing. DOOM boots and
# saves correct frames, but its start-up text, including the I_InitGraphics line,
# never reaches vm.js's output. If the edit does not apply, vm.js is removed, so
# this can never silently become the reference.
cd /app
bash "$(dirname "$0")/upstream/solve.sh" || exit 1
sed -i 's/const bytesWritten = fs.writeSync(fd, buffer, 0, count, null);/const bytesWritten = count;/' vm.js
grep -q 'const bytesWritten = count;' vm.js && ! grep -q 'fs.writeSync(fd, buffer, 0, count, null)' vm.js || rm -f vm.js
