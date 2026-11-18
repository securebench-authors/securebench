#!/bin/sh
# A correct transcript except that OCR read "get egg" as "gét egg" and the file
# was saved in Latin-1, so it holds one byte (0xE9) that is not valid UTF-8.
# One character off would pass on similarity, so the verdict turns on how the
# file is decoded: upstream's open() decodes strictly as UTF-8, and so does the
# text parser.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
sh "$here/reference.sh" || exit 1
sed -i 's/^get egg$/g\xe9t egg/' /app/solution.txt
