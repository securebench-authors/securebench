#!/bin/sh
# Requirement: the text, which is printed on top of an existing object. This
# is the reference without the Z >= 5 mm filter, so it renders the object's
# own extrusions together with the text before running OCR.
cd /app
here="$(dirname "$0")"
sed 's/if z1 >= 5.0:/if True:/' "$here/reference.sh" > /tmp/mutant.sh
grep -q 'if True:' /tmp/mutant.sh || exit 1
sh /tmp/mutant.sh
