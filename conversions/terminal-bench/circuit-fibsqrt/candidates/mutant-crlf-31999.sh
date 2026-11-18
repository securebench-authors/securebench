#!/bin/sh
# The reference circuit padded with 11,895 blank CRLF lines, for 31,999 lines
# in Python text mode, where "\r\n" is one line ending. Under the limit, and
# the simulator ignores the padding, so both graders should pass it. An Oracle
# that counted "\r" and "\n" separately would see 43,894 lines and fail it.
sh "$(dirname "$0")/reference.sh" || exit 1
cd /app || exit 1
python3 -c 'import sys; sys.stdout.write("\r\n" * 11895)' >> gates.txt
