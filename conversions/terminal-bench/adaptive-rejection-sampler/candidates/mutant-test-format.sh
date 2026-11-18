#!/bin/sh
# The test function's output format (upstream
# test_formal_testing_with_known_truth). The reference, with test() reporting
# "Normal Distribution passed" instead of "TEST_NAME: PASS".
here=$(cd "$(dirname "$0")" && pwd)
sh "$here/reference.sh" || exit 1
cd /app
sed -i -e 's/\(Distribution\|Validation\): PASS/\1 passed/' -e 's/\(Distribution\|Validation\): FAIL/\1 failed/' ars.R
grep -q 'Normal Distribution passed' ars.R || exit 1
! grep -q ': PASS\|: FAIL' ars.R || exit 1
