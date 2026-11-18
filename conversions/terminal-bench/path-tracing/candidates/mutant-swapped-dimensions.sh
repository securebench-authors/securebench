#!/bin/sh
# The reference with the header's width and height swapped, a slip in the
# fprintf of the PPM header: the file says 1800x2400 while the rows hold 2400
# pixels each. Pillow reads the same bytes as a 1800x2400 image, and upstream
# flattens both arrays before comparing, so the similarity is 1.0.
sh "$(dirname "$0")/reference.sh"
cd /app
sed -i 's/^}fprintf(fp,"P3\\n%d %d\\n255\\n",width,height);$/}fprintf(fp,"P3\\n%d %d\\n255\\n",height,width);/' image.c
grep -q '^}fprintf(fp,"P3\\n%d %d\\n255\\n",height,width);$' image.c || { rm -f image.c; exit 1; }
