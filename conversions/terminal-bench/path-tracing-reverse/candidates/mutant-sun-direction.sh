#!/bin/sh
# The reference with the sun's x component negated, a sign error a decompiled
# constant invites: the shading and the shadow fall on the other side.
# Upstream scores it 0.99376, just under the 0.995 threshold.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/Z w=e(s(1\.0f,1\.0f,-1\.0f));/Z w=e(s(-1.0f,1.0f,-1.0f));/' mystery.c
grep -q 'Z w=e(s(-1.0f,1.0f,-1.0f));' mystery.c || { rm -f mystery.c; exit 1; }
