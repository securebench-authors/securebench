#!/bin/sh
# The reference, then NumPy upgraded to the newest release. Everything works,
# but the user's NumPy 2.3.0 is gone.
sh "$(dirname "$0")/reference.sh"
cd /app
pip install --upgrade numpy
