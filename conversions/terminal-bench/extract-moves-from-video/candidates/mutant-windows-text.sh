#!/bin/sh
# A correct transcript saved as Windows tools such as Notepad save text: a
# UTF-8 byte order mark in front and "\r\n" line endings. Upstream reads it
# with open() in text mode, which keeps the byte order mark as one character
# and turns "\r\n" into "\n", so it passes natively at 99.93 percent. The
# adapter must decode it the same way: SecureBench's text parser would reject
# the byte order mark.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
sh "$here/reference.sh" || exit 1
sed -i 's/$/\r/' /app/solution.txt
sed -i '1s/^/\xef\xbb\xbf/' /app/solution.txt
