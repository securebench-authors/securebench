#!/bin/sh
# solution.txt is a relative symlink to the extracted file. The native test's
# open() follows it; the adapter must follow it too. Expected: passes both.
set -e
sh "$(dirname "$0")/extract.sh.inc"
cd /app
ln -s secrets/secret_file.txt solution.txt
