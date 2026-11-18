#!/bin/sh
# Found by the review. The reference, then the compile command from the
# instructions, which leaves cmain beside the source.
sh "$(dirname "$0")/reference.sh"
cd /app
gcc /app/polyglot/main.py.c -o /app/polyglot/cmain
