#!/bin/sh
# A transcript that keeps Zork's ">" input prompt in front of every move, as an
# OCR of the input line would read it. The 280 extra characters put the file
# far enough from the expected length that the Oracle decides on the length
# bound alone, without running the distance loop.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
sh "$here/reference.sh" || exit 1
sed -i 's/^/>/' /app/solution.txt
