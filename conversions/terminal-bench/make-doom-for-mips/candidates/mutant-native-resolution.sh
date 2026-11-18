#!/bin/sh
# The reference built at DOOM's native 320x200 instead of doomgeneric's default
# 640x400, a common simplification for a slow emulator. Start-up text is the
# same, but every frame is 320x200.
sh "$(dirname "$0")/reference.sh"
cd /app/doomgeneric/doomgeneric
sed -i 's/#define DOOMGENERIC_RESX 640/#define DOOMGENERIC_RESX 320/; s/#define DOOMGENERIC_RESY 400/#define DOOMGENERIC_RESY 200/' doomgeneric.h
grep -q 'DOOMGENERIC_RESX 320' doomgeneric.h || { rm -f /app/doomgeneric_mips; exit 1; }
make clean && make all && cp doomgeneric_mips ../..
