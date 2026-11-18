#!/bin/sh
# The reference circuit padded with blank lines and a final comment line
# without a newline, for exactly 32,000 lines. The simulator ignores the
# padding; upstream's `line_count < 32000` rejects it, counting the
# unterminated last line.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app || exit 1
python3 -c 'import sys; sys.stdout.write("\n" * 11895 + "# end")' >> gates.txt
