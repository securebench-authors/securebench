#!/bin/sh
# The reference with the R/B swap that the comment in doomgeneric_img.c's
# writeBMPFile describes ("Swap R and B (RGBA to BGRA)") actually performed, so
# every frame is written with red and blue exchanged.
sh "$(dirname "$0")/reference.sh"
cd /app/doomgeneric/doomgeneric
sed -i 's|\*pixel_data++ = pixel;|*pixel_data++ = (pixel \& 0xff00ff00) \| ((pixel >> 16) \& 0xff) \| ((pixel \& 0xff) << 16);|' doomgeneric_img.c
grep -q 'pixel >> 16' doomgeneric_img.c || { rm -f /app/doomgeneric_mips; exit 1; }
make all && cp doomgeneric_mips ../..
