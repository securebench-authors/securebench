#!/bin/sh
# Requirement: the text as it reads on the print. This is the reference with
# a plain top-down view (no rotation) in place of its 201 degree turn about
# Y, so the text reaches OCR mirrored.
cd /app
here="$(dirname "$0")"
sed 's/^python3 render.py 0 201 0$/python3 render.py 0 0 0/' "$here/reference.sh" > /tmp/mutant.sh
grep -q '^python3 render.py 0 0 0$' /tmp/mutant.sh || exit 1
sh /tmp/mutant.sh
