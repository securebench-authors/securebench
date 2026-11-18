#!/bin/sh
# The reference with close(2) forgetting to write a file's buffered contents back
# to disk. open(2) still creates /tmp/frame.bmp, so the frame appears, but it
# stays empty. If the edit does not apply, vm.js is removed.
cd /app
bash "$(dirname "$0")/upstream/solve.sh" || exit 1
sed -i 's/fs.writeFileSync(fileInfo.path, fileInfo.data);/fileInfo.modified = false;/' vm.js
grep -q 'fileInfo.modified = false;' vm.js && ! grep -q 'fs.writeFileSync(fileInfo.path, fileInfo.data)' vm.js || rm -f vm.js
