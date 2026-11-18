#!/bin/sh
# The reference circuit (20,104 lines) followed by 11,896 lone carriage
# returns. The simulator reads lines with fgets, which splits only on "\n",
# so it ignores the padding and prints correct answers. Upstream counts lines
# in Python text mode, where each lone "\r" ends a line: 32,000 lines, so
# upstream fails it. The conversion's Oracle must count the same way.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app || exit 1
python3 -c 'import sys; sys.stdout.write("\r" * 11896)' >> gates.txt
