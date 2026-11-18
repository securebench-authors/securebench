#!/bin/sh
# The reference with I_SetPalette's gamma table left out, so the WAD's palette is
# written as it is. Gamma row 0 is close to the identity, so the title scores
# about 0.9565 against reference.jpg, just above upstream's 0.95 and below the
# reference's 0.9571. This exercises the score near its threshold.
sh "$(dirname "$0")/reference.sh"
cd /app/doomgeneric/doomgeneric
sed -i 's/gammatable\[usegamma\]\[\*palette++\]/*palette++/' i_video.c
grep -q 'colors\[i\]\.r = \*palette++;' i_video.c || { rm -f /app/doomgeneric_mips; exit 1; }
make all && cp doomgeneric_mips ../..
