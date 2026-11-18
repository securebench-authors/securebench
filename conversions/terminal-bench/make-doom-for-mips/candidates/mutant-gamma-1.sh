#!/bin/sh
# The reference with doomgeneric's gamma correction at level 1 instead of the
# default 0, as if the brightness had been raised once in the menu. Every frame
# is slightly brighter: the title scores about 0.946 against reference.jpg,
# just below upstream's 0.95, so this exercises the score near its threshold.
sh "$(dirname "$0")/reference.sh"
cd /app/doomgeneric/doomgeneric
sed -i 's/^int usegamma = 0;/int usegamma = 1;/' i_video.c
grep -q '^int usegamma = 1;' i_video.c || { rm -f /app/doomgeneric_mips; exit 1; }
make all && cp doomgeneric_mips ../..
