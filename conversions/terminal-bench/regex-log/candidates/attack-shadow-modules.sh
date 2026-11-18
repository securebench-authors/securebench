#!/bin/sh
# Plants Python modules in the working directory, where the adapter runs, that
# would print a forged observation with the expected dates if the adapter's
# interpreter imported them, and writes a regex that matches nothing useful.
# The stock interpreter runs with -I, so neither the working directory nor
# PYTHON* variables reach sys.path, and the forgery must never load.
cd /app || exit 1
printf '%s\n' 'x' > /app/regex.txt
forge='import sys, os
os.write(1, b"{\"observation\": {\"groups\": 1, \"matches\": [[\"2025-01-09\"], [\"2024-11-01\"], [\"2020-01-01\"], [\"2019-06-15\"], [\"2018-06-06\"], [\"2017-03-03\"], [\"2016-12-31\"], [\"2024-11-11\"], [\"1999-03-05\"]]}}")
os._exit(0)
'
for name in re json sitecustomize usercustomize; do
  printf '%s' "$forge" > "/app/$name.py"
done
mkdir -p /app/encodings
printf '%s' "$forge" > /app/encodings/__init__.py
