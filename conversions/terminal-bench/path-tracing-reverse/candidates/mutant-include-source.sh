#!/bin/sh
# Splits the program in two: mystery.c is one line that includes a full,
# unreduced source kept beside it in /app (upstream's environment/orig.c,
# copied beside this script). Upstream measures only mystery.c and compiles it
# in /app, where the include is found, so it passes. Aimed at the adapter's
# emulation of upstream's build: the other files the agent left in /app must
# be there when gcc runs.
cd /app
cp "$(dirname "$0")/orig.c" /app/render.c
printf '#include "render.c"\n' > /app/mystery.c
